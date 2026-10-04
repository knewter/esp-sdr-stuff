#!/usr/bin/env python3
"""Separate fixed timer-qualified zero-data primary source; no air denominator.

The v1 module supplies unchanged wire/event/command primitives. Its validators,
runner, CLI and globals are never replaced. Only this explicitly selected
entrypoint can request the finite timed-v2 profile.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import signal
import socket
import sys
import time

import ble_direct_hci_source as v1

PROFILE = 'extended-primary-zero-data-timed-v2'
STEPS = ('set_parameters', 'set_data', 'enable', 'cleanup_disable', 'cleanup_remove')
MIN_ENABLED_SECONDS = 24.0
MAX_ENABLED_SECONDS = 30.0
COMMAND_SECONDS = 2.0
BOUND_SECONDS = 45.0
ENABLE_RESERVE_SECONDS = 32.0


def parent_deadline(value):
    if type(value) is not int or not 0 < value <= 2**63-1:
        raise ValueError('positive integer monotonic deadline required')
    return value / 1e9


def validate_profile(profile=PROFILE, handle=1, interval_ms=20, events=0,
                     duration_ms=25000, start_delay=0):
    for actual, expected in ((profile, PROFILE), (handle, 1), (interval_ms, 20),
                             (events, 0), (duration_ms, 25000)):
        if type(actual) is not type(expected) or actual != expected:
            raise ValueError('exact fixed timed-v2 profile required')
    if type(start_delay) not in (int, float) or not math.isfinite(start_delay) or start_delay != 0:
        raise ValueError('timed-v2 start delay must be zero')


def validate_options(argv):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--profile', required=True)
    cli.add_argument('--handle', type=int, default=1)
    cli.add_argument('--interval-ms', type=int, default=20)
    cli.add_argument('--events', type=int, default=0)
    cli.add_argument('--duration-ms', type=int, default=25000)
    cli.add_argument('--start-delay', type=float, default=0)
    cli.add_argument('--parent-deadline-monotonic-ns', type=int)
    args = cli.parse_args(argv)
    try:
        validate_profile(**{k: v for k, v in vars(args).items() if k != 'parent_deadline_monotonic_ns'})
        if args.parent_deadline_monotonic_ns is not None:
            parent_deadline(args.parent_deadline_monotonic_ns)
    except ValueError as error:
        cli.error(str(error))
    return args


def enable_frame(enabled):
    if type(enabled) is not bool:
        raise ValueError('enable must be boolean')
    return bytes.fromhex('010101c40900' if enabled else '000101000000')


class TimedSource(v1.Source):
    """Owned local subclass; strict clocks/order supplement the v1 primitives."""
    def __init__(self, sock, emit, deadline=None, *, deadline_ns=None):
        self._sink = emit
        self._phase = None
        self._command_deadline = None
        self._event_deadline = None
        self.enable_ack_ns = None
        self.enable_send_ns = None
        self.cancelled = False
        self.cleaning = False
        self.used = False
        own_ns = time.monotonic_ns() + int(BOUND_SECONDS*1e9)
        if deadline is not None:
            own_ns = min(own_ns, int(deadline*1e9))
        self.deadline_ns = min(own_ns, deadline_ns) if deadline_ns is not None else own_ns
        self.deadline = self.deadline_ns / 1e9
        self.cleanup_deadline = None
        super().__init__(sock, self._record, command_timeout=COMMAND_SECONDS)
        self.handle = 1

    def cancel(self, *_):
        # Repeated requests are deferred through the two bounded cleanup ACKs.
        self.cancelled = True

    def _clock(self):
        if self.cancelled and not self.cleaning:
            raise KeyboardInterrupt()
        if not self.cleaning and time.monotonic_ns() >= self.deadline_ns:
            raise v1.SourceError('timed_operation_deadline')
        normal = self.cleanup_deadline if self.cleaning else self.deadline
        deadlines = [d for d in (normal, self._command_deadline, self._event_deadline) if d is not None]
        if deadlines and time.monotonic() >= min(deadlines):
            raise v1.SourceError('timed_operation_deadline')

    def _record(self, record):
        # Discard undefined selected-power bytes on failed2036 responses.
        if record.get('hci_opcode_hex') == '2036' and record.get('status', 0) != 0:
            record.pop('controller_selected_tx_power_dbm', None)
        record['monotonic_ns'] = time.monotonic_ns()
        self._sink(dict(record))
        self._clock()  # Includes a slow emitter/fsync/pipe return.
        kind = record['kind']
        if kind == 'command_sent' and record.get('step') == 'enable':
            if self.deadline_ns - time.monotonic_ns() < int(ENABLE_RESERVE_SECONDS*1e9):
                raise v1.SourceError('insufficient_enable_reserve')
        if kind in ('command_complete', 'command_status'):
            expected = self._phase[1] if self._phase else None
            if record.get('hci_opcode_hex') != expected:
                raise v1.SourceError('unexpected_or_duplicate_ack')
            if kind == 'command_complete' and expected == '2036' and record['status'] == 0:
                power = record.get('controller_selected_tx_power_dbm')
                if type(power) is not int or not -127 <= power <= 20:
                    raise v1.SourceError('selected_power_invalid')
        if kind == 'termination_observed':
            if self.enable_ack_ns is None:
                raise v1.SourceError('termination_before_enable_ack')
            if len(self.terminations) != 1:
                raise v1.SourceError('duplicate_termination')

    def event(self, until):
        self._event_deadline = until
        try:
            # The unchanged v1 parser is reused directly; its receive loop does
            # not poll our deferred cancellation flag or post-recv clock.
            while time.monotonic() < until:
                self._clock()
                active = self.cleanup_deadline if self.cleaning else self.deadline
                self.sock.settimeout(min(.2, max(.001, min(until, active)-time.monotonic())))
                try:
                    packet = self.sock.recv(65535)
                except TimeoutError:
                    self._clock()
                    continue
                parsed = v1.parse_event(packet, self.handle)
                if parsed is not None:
                    if parsed['kind'] == 'termination_observed':
                        parsed['observed_after_enable_command_sent'] = self.enable_sent
                        self.terminations.append(parsed)
                    self.emit(parsed)  # Records even a late ACK, then refuses.
                    self._clock()
                    return parsed
                self._clock()
            raise v1.SourceError('event_timeout')
        finally:
            self._event_deadline = None

    def command(self, step, opcode, payload):
        self._phase = (step, f'{opcode:04x}')
        self._command_deadline = time.monotonic() + COMMAND_SECONDS
        try:
            self._clock()
            active = self.cleanup_deadline if self.cleaning else self.deadline
            self.sock.settimeout(min(COMMAND_SECONDS, active-time.monotonic()))
            self.emit({'kind': 'command_sent', 'step': step, 'hci_opcode_hex': f'{opcode:04x}',
                       'advertising_handle': self.handle})
            frame = v1.command_frame(opcode, payload)
            self._clock()  # Includes frame construction before any send.
            if step == 'enable':
                if self.deadline_ns-time.monotonic_ns() < int(ENABLE_RESERVE_SECONDS*1e9):
                    raise v1.SourceError('insufficient_enable_reserve')
                self.enable_sent = True
                self.enable_send_ns = time.monotonic_ns()
            sent = self.sock.send(frame)
            self._clock()
            if sent != len(frame):
                raise v1.SourceError('short_command_send')
            result = self.event(self._command_deadline)
            self.emit({'kind': 'command_result', 'step': step,
                       **{k: v for k, v in result.items() if k != 'kind'}})
            self._clock()
            if result['kind'] != 'command_complete' or result['status'] != 0:
                raise v1.SourceError('command_rejected_or_unexpected_status', result['status'])
            self.accepted_steps.add(step)
            if step == 'enable':
                self.enable_ack_ns = result['monotonic_ns']
            return result
        finally:
            self._phase = None
            self._command_deadline = None

    def run_timed(self):
        if self.used:
            raise ValueError('timed source instances cannot restart')
        self.used = True
        summary = {'kind': 'source_closed', 'source_profile': PROFILE,
                   'advertising_handle': 1, 'event_properties': 0,
                   'extended_mode_diagnostic_requested': True,
                   'primary_zero_data_diagnostic_requested': True,
                   'advertising_data_length': 0, 'duration_10ms_units': 2500,
                   'duration_diagnostic_requested': True,
                   'unlimited_events_diagnostic_requested': True,
                   'termination_count_field_meaningful': False,
                   'controller_completed_count_verified': False,
                   'controller_timed_profile_verified': False,
                   'handle_diagnostic_requested': True,
                   'automatic_restarts': 0, 'automatic_fallbacks': 0,
                   'independently_observed_air_emission_count': None,
                   'episode_deadline_monotonic_ns': self.deadline_ns,
                   'enable_reserve_seconds': ENABLE_RESERVE_SECONDS,
                   'cleanup': {}, 'status': 'trial_failed'}
        verified = False
        try:
            self.command('set_parameters', 0x2036, v1.parameters(20, 1, True))
            self.command('set_data', 0x2037, v1.advertising_data(1, True))
            self.emit({'kind': 'source_ready', 'advertising_handle': 1,
                       'parameter_and_data_commands_accepted': True, 'start_delay_s': 0})
            self._clock()
            if self.deadline_ns - time.monotonic_ns() < int(ENABLE_RESERVE_SECONDS*1e9):
                raise v1.SourceError('insufficient_enable_reserve')
            self.command('enable', 0x2039, enable_frame(True))
            self.emit({'kind': 'source_enabled', 'advertising_handle': 1,
                       'enable_command_accepted': True, 'max_extended_advertising_events': 0,
                       'enable_send_monotonic_ns': self.enable_send_ns,
                       'unlimited_events_diagnostic_requested': True, 'duration_10ms_units': 2500})
            until = self.enable_ack_ns / 1e9 + MAX_ENABLED_SECONDS
            while not self.terminations:
                self.event(until)
            term = self.terminations[0]
            elapsed = (term['monotonic_ns'] - self.enable_ack_ns) / 1e9
            count = term['controller_reported_completed_extended_advertising_events']
            if (term['status'] != 0x3c or not term['observed_after_enable_command_sent'] or
                    type(count) is not int or not 0 <= count <= 255 or
                    not MIN_ENABLED_SECONDS <= elapsed < MAX_ENABLED_SECONDS):
                raise v1.SourceError('timer_status_interval_or_metadata_invalid')
            summary['observed_enabled_seconds'] = elapsed
            summary['completed_count_metadata_anomaly'] = count != 0
            verified = True
        except v1.SourceError as error:
            summary['error_code'] = str(error)
        except OSError as error:
            summary.update(status='transport_failed', error_errno=error.errno)
        except KeyboardInterrupt:
            self.cancelled = True
            summary['status'] = 'interrupted'
        finally:
            self.cleaning = True
            # Independent bounded failure cleanup never extends qualification.
            self.cleanup_deadline = max(self.deadline, time.monotonic() + 2*COMMAND_SECONDS)
            for step, opcode, payload in (
                    ('cleanup_disable', 0x2039, enable_frame(False)),
                    ('cleanup_remove', 0x203c, b'\x01')):
                try:
                    result = self.command(step, opcode, payload)
                    summary['cleanup'][step] = {'status': result['status'], 'command_complete_received': True}
                except v1.SourceError as error:
                    summary['cleanup'][step] = {'error_code': str(error), 'status': error.status, 'success': False}
                except OSError as error:
                    summary['cleanup'][step] = {'error_errno': error.errno, 'success': False}
                except KeyboardInterrupt:
                    self.cancelled = True
                    summary['cleanup'][step] = {'error_code': 'interrupted_during_cleanup', 'success': False}
            self.cleaning = False
            if self.terminations:
                summary['termination'] = {k: v for k, v in self.terminations[0].items() if k != 'monotonic_ns'}
            summary['termination_events_observed'] = len(self.terminations)
            summary['enable_send_monotonic_ns'] = self.enable_send_ns
            summary['accepted_steps'] = sorted(self.accepted_steps)
            summary['cleanup_success'] = all(summary['cleanup'][s].get('status') == 0 and
                summary['cleanup'][s].get('command_complete_received') is True for s in STEPS[-2:])
            qualified = verified and len(self.terminations) == 1 and summary['cleanup_success'] and not self.cancelled
            qualified = qualified and time.monotonic_ns() < self.deadline_ns
            summary['controller_timed_profile_verified'] = qualified
            if qualified:
                summary['status'] = 'controller_timed_profile_verified'
            elif self.cancelled:
                summary['status'] = 'interrupted'
            elif verified:
                summary['status'] = 'cleanup_failed'
            # Final summary is outside command/event clocks; cancellation here
            # still prevents the CLI's post-socket-close success decision.
            self.cleaning = True
            written_qualified = summary['controller_timed_profile_verified']
            try:
                self.emit(summary)
            except v1.SourceError as error:
                summary.update(controller_timed_profile_verified=False,
                               status='terminal_output_deadline', error_code=str(error))
                summary['monotonic_ns'] = time.monotonic_ns()
                self._sink(dict(summary))  # Failed correction; never qualifies.
                written_qualified = False
            finally:
                self.cleaning = False
            if self.cancelled:
                summary['controller_timed_profile_verified'] = False
                summary['status'] = 'interrupted'
            if time.monotonic_ns() >= self.deadline_ns:
                summary['controller_timed_profile_verified'] = False
                summary['status'] = 'episode_deadline_exceeded'
            if written_qualified and not summary['controller_timed_profile_verified']:
                summary['monotonic_ns'] = time.monotonic_ns()
                self._sink(dict(summary))  # Replace a cancelled/late candidate.
        return summary


def configuration():
    return {'kind': 'configuration_requested', 'source_profile': PROFILE,
            'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'v1_primitives_sha256': hashlib.sha256(Path(v1.__file__).read_bytes()).hexdigest(),
            'advertising_handle': 1, 'event_properties': 0,
            'extended_mode_diagnostic_requested': True, 'primary_channel_map': 1,
            'own_address_type': 0, 'primary_phy': 1, 'secondary_phy': 1,
            'peer_address_type': 0, 'unused_peer_address_zero': True,
            'filter_policy': 0, 'tx_power_request': 127, 'secondary_max_skip': 0,
            'advertising_sid': 0, 'scan_request_notification_enable': 0,
            'enable_reserve_seconds': ENABLE_RESERVE_SECONDS,
            'interval_ms': 20, 'advertising_data_length': 0,
            'owned_manufacturer_ad_exact_match': False,
            'primary_zero_data_diagnostic_requested': True, 'primary_header_ownership_observed': False,
            'max_extended_advertising_events': 0, 'duration_10ms_units': 2500,
            'duration_diagnostic_requested': True, 'unlimited_events_diagnostic_requested': True,
            'termination_count_field_meaningful': False, 'handle_diagnostic_requested': True,
            'independently_observed_air_emission_count': None,
            'operator_preconditions': 'Exclusive identity-selected hci0, powered/idle and handle1 reservation checked externally; no concurrent advertising commands.'}


def emit_stdout(record):
    row = dict(record)
    row.setdefault('monotonic_ns', time.monotonic_ns())
    row['utc'] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(row, sort_keys=True), flush=True)


def main(argv=None):
    began_ns = time.monotonic_ns()
    args = validate_options(sys.argv[1:] if argv is None else argv)  # Before socket access.
    deadline_ns = began_ns + int(BOUND_SECONDS*1e9)
    if args.parent_deadline_monotonic_ns is not None:
        deadline_ns = min(deadline_ns, args.parent_deadline_monotonic_ns)
    deadline = deadline_ns / 1e9
    config = configuration()
    config['episode_deadline_monotonic_ns'] = deadline_ns
    emit_stdout(config)
    sock = None
    source = None
    summary = None
    interrupted = False
    def cancel(*_):
        nonlocal interrupted
        interrupted = True
        if source is not None:
            source.cancel()
    handlers = {s: signal.signal(s, cancel) for s in (signal.SIGINT, signal.SIGTERM)}
    code = 2
    try:
        if interrupted or time.monotonic_ns() >= deadline_ns:
            return 2
        sock = socket.socket(31, socket.SOCK_RAW, 1)
        v1.bind_raw(sock)
        source = TimedSource(sock, emit_stdout, deadline_ns=deadline_ns)
        if interrupted:
            source.cancel()
        emit_stdout({'kind': 'source_socket_ready', 'hci_device': 0, 'hci_channel': 0})
        summary = source.run_timed()
        code = 0 if summary['controller_timed_profile_verified'] else 2
    except OSError as error:
        emit_stdout({'kind': 'source_closed', 'source_profile': PROFILE,
                     'status': 'socket_or_bind_failed', 'error_errno': error.errno,
                     'controller_timed_profile_verified': False,
                     'independently_observed_air_emission_count': None})
    finally:
        try:
            if sock is not None:
                closed = False
                closure_error = None
                closure_failed = False
                try:
                    sock.close()
                    closed = True
                    emit_stdout({'kind': 'source_socket_closed'})
                except OSError as error:
                    code = 2
                    closure_error = error.errno
                    closure_failed = True
                if summary is not None and summary['controller_timed_profile_verified'] and (
                        not closed or closure_failed or interrupted or source.cancelled or
                        time.monotonic_ns() >= deadline_ns):
                    code = 2
                    correction = dict(summary)
                    correction.update(controller_timed_profile_verified=False,
                        status='post_socket_closure_deadline_cancel_or_error',
                        source_socket_closed=closed, error_errno=closure_error,
                        monotonic_ns=time.monotonic_ns())
                    emit_stdout(correction)
        finally:
            for sig, handler in handlers.items():
                signal.signal(sig, handler)
    return code if time.monotonic_ns() < deadline_ns and not interrupted and not (source is not None and source.cancelled) else 2


if __name__ == '__main__':
    raise SystemExit(main())
