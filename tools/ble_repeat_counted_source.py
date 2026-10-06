#!/usr/bin/env python3
"""Repeated controller-counted zero-data extended advertising on HCI0 handle1.

One socket configures the existing extended-primary-zero-data-v1 wire profile
once, then re-enables the same owned set for consecutive 255-event cycles.
Each cycle must end with LE Advertising Set Terminated status 0x43 and count
255; anything else stops the run and is retained. Sanitized JSONL only.

Counts are controller-completed advertising events, not independently observed
air emissions. Run inside the scoped container (see ble_repeat_source_container).
"""
import argparse
import hashlib
from pathlib import Path
import signal
import socket
import sys
import time

from ble_direct_hci_source import (SourceError, Source, advertising_data, bind_raw,
                                   emit_stdout, enable, interrupt_source, parameters)

PROFILE = 'extended-primary-zero-data-v1-repeat255'
HANDLE = 1
INTERVAL_MS = 20
EVENTS_PER_CYCLE = 255
MAX_CYCLES = 400
# Controller adds 0..10ms advDelay per event; allow 5s slack.
CYCLE_TIMEOUT_S = EVENTS_PER_CYCLE*(INTERVAL_MS/1000+.010)+5


def validate_cycles(cycles):
    if type(cycles) is not int or not 1 <= cycles <= MAX_CYCLES:
        raise ValueError(f'cycles must be 1..{MAX_CYCLES}')
    return cycles


def run_cycles(source, cycles, start_delay=1.0, cycle_timeout_s=None):
    """Drive `cycles` counted enables on one configured set; always clean up."""
    validate_cycles(cycles)
    source.handle = HANDLE
    enable_frame = enable(True, EVENTS_PER_CYCLE, 0, HANDLE)
    summary = {'kind': 'source_closed', 'profile': PROFILE, 'advertising_handle': HANDLE,
               'cycles_requested': cycles, 'events_per_cycle': EVENTS_PER_CYCLE,
               'cycles_verified': 0, 'controller_counted_events_total': 0,
               'independently_observed_air_emission_count': None,
               'automatic_restarts': 0, 'cleanup': {}}
    try:
        source.command('set_parameters', 0x2036, parameters(INTERVAL_MS, HANDLE, True))
        source.command('set_data', 0x2037, advertising_data(HANDLE, True))
        if source.terminations:
            raise SourceError('termination_before_enable')
        source.emit({'kind': 'source_ready', 'advertising_handle': HANDLE, 'start_delay_s': start_delay})
        time.sleep(start_delay)
        for cycle in range(cycles):
            source.terminations.clear()
            source.command('enable', 0x2039, enable_frame)
            source.emit({'kind': 'cycle_enabled', 'cycle': cycle})
            until = time.monotonic()+(CYCLE_TIMEOUT_S if cycle_timeout_s is None else cycle_timeout_s)
            while not source.terminations:
                source.event(until)
            term = source.terminations[0]
            if (len(source.terminations) != 1 or term['status'] != 0x43 or
                    term['controller_reported_completed_extended_advertising_events'] != EVENTS_PER_CYCLE):
                summary['failed_cycle'] = cycle
                summary['failed_termination'] = term
                raise SourceError('termination_status_or_count_mismatch')
            summary['cycles_verified'] += 1
            summary['controller_counted_events_total'] += EVENTS_PER_CYCLE
            source.emit({'kind': 'cycle_verified', 'cycle': cycle,
                         'controller_reported_completed_extended_advertising_events': EVENTS_PER_CYCLE})
        summary['status'] = 'all_cycles_counted'
    except SourceError as error:
        summary['status'] = 'trial_failed'
        summary['error_code'] = str(error)
    except OSError as error:
        summary['status'] = 'transport_failed'
        summary['error_errno'] = error.errno
    except KeyboardInterrupt:
        summary['status'] = 'interrupted'
    finally:
        for step, opcode, payload in [('cleanup_disable', 0x2039, enable(False, EVENTS_PER_CYCLE, handle=HANDLE)),
                                      ('cleanup_remove', 0x203c, bytes([HANDLE]))]:
            try:
                result = source.command(step, opcode, payload)
                summary['cleanup'][step] = {'status': result['status']}
            except SourceError as error:
                summary['cleanup'][step] = {'error_code': str(error), 'status': error.status}
            except (OSError, KeyboardInterrupt) as error:
                summary['cleanup'][step] = {'error': type(error).__name__}
        summary['cleanup_success'] = all(step in source.accepted_steps
                                         for step in ('cleanup_disable', 'cleanup_remove'))
        source.emit(summary)
    return summary


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--cycles', type=int, required=True)
    cli.add_argument('--start-delay', type=float, default=1)
    args = cli.parse_args(argv)
    try:
        validate_cycles(args.cycles)
    except ValueError as error:
        cli.error(str(error))
    if not 0 <= args.start_delay <= 60:
        cli.error('start delay must be 0..60s')
    emit_stdout({'kind': 'configuration_requested', 'profile': PROFILE, 'advertising_handle': HANDLE,
                 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 'event_properties': 0, 'primary_channel_map': 1, 'primary_phy': 1, 'secondary_phy': 1,
                 'interval_ms': INTERVAL_MS, 'advertising_data_length': 0,
                 'events_per_cycle': EVENTS_PER_CYCLE, 'cycles': args.cycles, 'duration_10ms_units': 0})
    sock = None
    previous = signal.signal(signal.SIGTERM, interrupt_source)
    try:
        sock = socket.socket(31, socket.SOCK_RAW, 1)
        bind_raw(sock)
        summary = run_cycles(Source(sock, emit_stdout), args.cycles, args.start_delay)
    except OSError as error:
        emit_stdout({'kind': 'source_closed', 'status': 'socket_or_bind_failed', 'error_errno': error.errno})
        return 2
    finally:
        if sock is not None:
            sock.close()
        signal.signal(signal.SIGTERM, previous)
    return 0 if summary['status'] == 'all_cycles_counted' and summary['cleanup_success'] else 2


if __name__ == '__main__':
    sys.exit(main())
