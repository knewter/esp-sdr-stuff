#!/usr/bin/env python3
"""Operator-run, bounded HCI0 owned advertising source; sanitized JSONL only."""
import argparse
import ctypes
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import socket
import struct
import sys
import time

HANDLE = 0xef
OPCODES = {0x2036, 0x2037, 0x2039, 0x203c}
OWNED_AD = bytes.fromhex('0fffffff4553502d5344522d4556414c')


class SourceError(RuntimeError):
    def __init__(self, code, status=None):
        super().__init__(code)
        self.status = status


def raw_sockaddr():
    return struct.pack('=HHH', 31, 0, 0)  # Linux AF_BLUETOOTH,HCI0,RAW.


def event_filter():
    # Native struct hci_filter includes two trailing alignment bytes.
    return struct.pack('=IIIH', 1 << 4, (1 << 14) | (1 << 15), 1 << (62-32), 0)+bytes(2)


def bind_raw(sock):
    address = ctypes.create_string_buffer(raw_sockaddr())
    libc = ctypes.CDLL(None, use_errno=True)
    libc.bind.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint]
    libc.bind.restype = ctypes.c_int
    if libc.bind(sock.fileno(), address, 6) != 0:
        raise OSError(ctypes.get_errno(), 'HCI0 RAW bind failed')
    sock.setsockopt(0, 2, event_filter())  # SOL_HCI,HCI_FILTER; receive events only.


def parameters(interval_ms):
    if interval_ms not in (20, 100):
        raise ValueError('interval_ms must be 20 or 100')
    units = int(interval_ms/.625)
    return (bytes([HANDLE])+struct.pack('<H', 0x10)+units.to_bytes(3, 'little')*2
            +bytes([1, 0, 0])+bytes(6)+bytes([0, 0x7f, 1, 0, 1, 0, 0]))


def advertising_data():
    return bytes([HANDLE, 3, 1, len(OWNED_AD)])+OWNED_AD


def duration_units(duration_ms):
    if not isinstance(duration_ms, int) or (duration_ms != 0 and
            (not 100 <= duration_ms <= 5000 or duration_ms % 10)):
        raise ValueError('duration_ms must be 0 or 100..5000 in exact 10ms units')
    return duration_ms // 10


def enable(enabled, count=100, duration_ms=0):
    if not 1 <= count <= 255:
        raise ValueError('count must be 1..255')
    units = duration_units(duration_ms)
    # Num_Sets=1 scopes BOTH enable and cleanup disable to our handle.
    return (bytes([int(enabled), 1, HANDLE])
            +struct.pack('<H', units if enabled else 0)+bytes([count if enabled else 0]))


def command_frame(opcode, payload):
    if opcode not in OPCODES or len(payload) > 255:
        raise ValueError('unsupported_command')
    return bytes([1])+struct.pack('<HB', opcode, len(payload))+payload


def parse_event(packet):
    if len(packet) < 3 or packet[0] != 4 or len(packet) != 3+packet[2]:
        return None
    event = packet[1]
    data = packet[3:]
    if event == 0x0e and len(data) >= 4:
        opcode = struct.unpack_from('<H', data, 1)[0]
        if opcode not in OPCODES:
            return None
        lengths = (5,) if opcode == 0x2036 and data[3] == 0 else ((4, 5) if opcode == 0x2036 else (4,))
        if len(data) not in lengths:
            return None
        result = {'kind': 'command_complete', 'hci_opcode_hex': f'{opcode:04x}', 'status': data[3]}
        if len(data) == 5:
            result['controller_selected_tx_power_dbm'] = struct.unpack_from('b', data, 4)[0]
        return result
    if event == 0x0f and len(data) == 4:
        opcode = struct.unpack_from('<H', data, 2)[0]
        if opcode in OPCODES:
            return {'kind': 'command_status', 'hci_opcode_hex': f'{opcode:04x}', 'status': data[0]}
    if event == 0x3e and len(data) == 6 and data[0] == 0x12 and data[2] == HANDLE:
        return {'kind': 'termination_observed', 'status': data[1], 'advertising_handle': data[2],
                'controller_reported_completed_extended_advertising_events': data[5]}
    return None


class Source:
    def __init__(self, sock, emit, command_timeout=2):
        self.sock = sock
        self.emit = emit
        self.command_timeout = command_timeout
        self.terminations = []
        self.accepted_steps = set()
        self.enable_sent = False

    def event(self, until):
        while time.monotonic() < until:
            self.sock.settimeout(min(.2, max(.001, until-time.monotonic())))
            try:
                packet = self.sock.recv(65535)
            except TimeoutError:
                continue
            parsed = parse_event(packet)
            if parsed is not None:
                if parsed['kind'] == 'termination_observed':
                    parsed['observed_after_enable_command_sent'] = self.enable_sent
                    self.terminations.append(parsed)
                self.emit(parsed)
                return parsed
        raise SourceError('event_timeout')

    def command(self, step, opcode, payload):
        self.emit({'kind': 'command_sent', 'step': step, 'hci_opcode_hex': f'{opcode:04x}',
                   'advertising_handle': HANDLE})
        frame = command_frame(opcode, payload)
        if step == 'enable':
            self.enable_sent = True
        if self.sock.send(frame) != len(frame):
            raise SourceError('short_command_send')
        until = time.monotonic()+self.command_timeout
        while True:
            result = self.event(until)
            if result.get('hci_opcode_hex') != f'{opcode:04x}':
                continue
            self.emit({'kind': 'command_result', 'step': step, **{k:v for k,v in result.items() if k != 'kind'}})
            if result['kind'] != 'command_complete' or result['status'] != 0:
                raise SourceError('command_rejected_or_unexpected_status', result['status'])
            self.accepted_steps.add(step)
            return result

    def run(self, interval_ms=20, count=100, start_delay=1, duration_ms=0):
        # Reject invalid diagnostic fields before any controller command.
        param_frame = parameters(interval_ms)
        enable_frame = enable(True, count, duration_ms)
        summary = {'kind': 'source_closed', 'advertising_handle': HANDLE,
                   'independently_observed_air_emission_count': None,
                   'automatic_restarts': 0, 'automatic_fallbacks': 0, 'cleanup': {},
                   'duration_10ms_units': duration_units(duration_ms),
                   'duration_diagnostic_requested': duration_ms != 0}
        attempted = False
        verified = False
        try:
            attempted = True
            self.command('set_parameters', 0x2036, param_frame)
            self.command('set_data', 0x2037, advertising_data())
            if self.terminations:
                raise SourceError('termination_before_enable')
            self.emit({'kind': 'source_ready', 'advertising_handle': HANDLE,
                       'parameter_and_data_commands_accepted': True, 'start_delay_s': start_delay})
            time.sleep(start_delay)
            self.command('enable', 0x2039, enable_frame)
            self.emit({'kind': 'source_enabled', 'advertising_handle': HANDLE,
                       'enable_command_accepted': True, 'max_extended_advertising_events': count,
                       'duration_10ms_units': duration_units(duration_ms)})
            # Controller adds advDelay; permit up to 10ms per event plus 5s.
            expected_wait = count*(interval_ms/1000+.010)
            if duration_ms:
                # Diagnostic compares the timer even if the limiter is broken;
                # duration begins at the first RF event, not the host ACK.
                expected_wait = duration_ms/1000
            until = time.monotonic()+expected_wait+5
            while not self.terminations:
                self.event(until)
            term = self.terminations[0]
            verified = (term['status'] == 0x43
                        and term['controller_reported_completed_extended_advertising_events'] == count)
            summary['termination'] = term
            if not verified:
                # Preserve actual 0x3c/count for diagnosis, never relax the
                # requested-limit/status0x43 success gate.
                raise SourceError('termination_status_or_count_mismatch')
            summary['status'] = 'controller_count_verified'
        except SourceError as error:
            summary['status'] = 'trial_failed'
            summary['error_code'] = str(error)
        except OSError as error:
            summary['status'] = 'transport_failed'
            summary['error_errno'] = error.errno
        except KeyboardInterrupt:
            summary['status'] = 'interrupted'
        finally:
            if attempted:
                for step, opcode, payload in [('cleanup_disable', 0x2039, enable(False, count)),
                                               ('cleanup_remove', 0x203c, bytes([HANDLE]))]:
                    try:
                        result = self.command(step, opcode, payload)
                        summary['cleanup'][step] = {'status': result['status'], 'command_complete_received': True}
                    except SourceError as error:
                        summary['cleanup'][step] = {'error_code': str(error), 'status': error.status, 'success': False}
                    except OSError as error:
                        summary['cleanup'][step] = {'error_errno': error.errno, 'success': False}
                    except KeyboardInterrupt:
                        summary['cleanup'][step] = {'error_code': 'interrupted_during_cleanup', 'success': False}
            summary['termination_events_observed'] = len(self.terminations)
            summary['accepted_steps'] = sorted(self.accepted_steps)
            if verified and (len(self.terminations) != 1 or not self.terminations[0]['observed_after_enable_command_sent']):
                verified = False
                summary['status'] = 'trial_failed'
                summary['error_code'] = 'termination_sequence_invalid'
            summary['controller_completed_count_verified'] = verified
            summary['cleanup_success'] = all(step in self.accepted_steps for step in ['cleanup_disable', 'cleanup_remove'])
            if verified and not summary['cleanup_success']:
                summary['status'] = 'cleanup_failed'
            self.emit(summary)
        return summary


def emit_stdout(record):
    record = {**record, 'monotonic_ns': time.monotonic_ns(), 'utc': datetime.now(timezone.utc).isoformat()}
    print(json.dumps(record, separators=(',', ':')), flush=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--interval-ms', type=int, choices=[20, 100], default=20)
    cli.add_argument('--events', type=int, default=100)
    cli.add_argument('--start-delay', type=float, default=1)
    cli.add_argument('--duration-ms', type=int, default=0,
                     help='Diagnostic only: 0 (default) or 100..5000 in multiples of 10 ms')
    args = cli.parse_args()
    if not 1 <= args.events <= 255 or not 0 <= args.start_delay <= 60:
        cli.error('Events must be 1..255; start delay must be 0..60s')
    try:
        units = duration_units(args.duration_ms)
    except ValueError as error:
        cli.error(str(error))
    script_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    emit_stdout({'kind': 'configuration_requested', 'advertising_handle': HANDLE, 'script_sha256': script_sha256,
                 'event_properties': 0x10, 'primary_channel_map': 1, 'primary_phy': 1,
                 'secondary_phy': 1, 'interval_ms': args.interval_ms,
                 'advertising_data_length': len(OWNED_AD), 'owned_manufacturer_ad_exact_match': True,
                 'max_extended_advertising_events': args.events, 'duration_10ms_units': units,
                 'duration_diagnostic_requested': args.duration_ms != 0,
                 'independently_observed_air_emission_count': None,
                 'operator_preconditions': 'Exclusive HCI0 source ownership, BlueZ ActiveInstances=0 checked externally, reserved handleEF available; no simultaneous same-opcode advertising commands.'})
    sock = None
    try:
        sock = socket.socket(31, socket.SOCK_RAW, 1)
        bind_raw(sock)
        emit_stdout({'kind': 'source_socket_ready', 'hci_device': 0, 'hci_channel': 0})
        summary = Source(sock, emit_stdout).run(args.interval_ms, args.events, args.start_delay, args.duration_ms)
    except OSError as error:
        emit_stdout({'kind': 'source_closed', 'status': 'socket_or_bind_failed', 'error_errno': error.errno,
                     'independently_observed_air_emission_count': None, 'cleanup_attempted': False})
        return 2
    finally:
        if sock is not None:
            sock.close()
            emit_stdout({'kind': 'source_socket_closed'})
    return 0 if summary['status'] == 'controller_count_verified' else 2


if __name__ == '__main__':
    sys.exit(main())
