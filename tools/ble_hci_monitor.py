#!/usr/bin/env python3
"""Read-only, bounded HCI0 advertising-control monitor with strict redaction.

Never sends HCI commands. Discards addresses, advertising bytes, names, foreign
traffic and all unspecified fields before writing metadata. Controller event
counts are explicitly distinguished from independently observed RF emissions.
"""
import argparse
import json
from pathlib import Path
import socket
import struct
import time

ADV_OPCODES = {0x2006, 0x200A, 0x2036, 0x2039}


def sanitized_packet(packet):
    if len(packet) < 6:
        return None
    kind, index, size = struct.unpack_from('<HHH', packet)
    data = packet[6:]
    if index != 0 or len(data) != size:
        return None
    if kind == 2 and len(data) >= 3:  # Linux HCI_MON_COMMAND_PKT
        opcode, length = struct.unpack_from('<HB', data)
        payload = data[3:]
        if len(payload) != length or opcode not in ADV_OPCODES:
            return None
        result = {'kind': 'advertising_command', 'hci_opcode_hex': f'{opcode:04x}'}
        if opcode == 0x2006 and len(payload) == 15:
            low, high = struct.unpack_from('<HH', payload)
            result.update(interval_min_ms=low * .625, interval_max_ms=high * .625,
                          advertising_type=payload[4], primary_channel_map=payload[13])
        elif opcode == 0x200A and len(payload) == 1:
            result['enabled'] = bool(payload[0])
        elif opcode == 0x2036 and len(payload) == 25:
            result.update(advertising_handle=payload[0], event_properties=struct.unpack_from('<H', payload, 1)[0],
                          interval_min_ms=int.from_bytes(payload[3:6], 'little') * .625,
                          interval_max_ms=int.from_bytes(payload[6:9], 'little') * .625,
                          primary_channel_map=payload[9], primary_phy=payload[20], secondary_phy=payload[22])
        elif opcode == 0x2039 and len(payload) >= 2 and len(payload) == 2 + 4 * payload[1]:
            result['enabled'] = bool(payload[0])
            result['sets'] = []
            for offset in range(2, len(payload), 4):
                handle, duration, maximum = struct.unpack_from('<BHB', payload, offset)
                result['sets'].append({'handle': handle, 'duration_10ms_units': duration,
                                       'maximum_extended_advertising_events': maximum})
        else:
            return None
        return result
    if kind == 3 and len(data) >= 2:  # Linux HCI_MON_EVENT_PKT
        event, length = data[:2]
        payload = data[2:]
        if len(payload) != length:
            return None
        if event == 0x0E and len(payload) >= 4:
            opcode = struct.unpack_from('<H', payload, 1)[0]
            if opcode in ADV_OPCODES:
                return {'kind': 'advertising_command_complete', 'hci_opcode_hex': f'{opcode:04x}', 'status': payload[3]}
        if event == 0x3E and len(payload) == 6 and payload[0] == 0x12:
            return {'kind': 'controller_advertising_set_terminated', 'status': payload[1],
                    'advertising_handle': payload[2],
                    'controller_reported_completed_extended_advertising_events': payload[5]}
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not .1 <= args.seconds <= 3600 or args.output.exists():
        parser.error('Use bounded seconds and a fresh output path')
    record = {'schema': 1, 'kind': 'read-only sanitized HCI0 advertising control',
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'independently_observed_air_emission_count': None, 'records': [],
              'limitations': 'HCI commands and controller-reported events are control-plane evidence. No independent RF emission counter. Unknown socket loss; unrelated traffic and addresses discarded before storage.'}
    with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI) as monitor:
        monitor.bind((0xffff, 3))  # HCI_DEV_NONE, HCI_CHANNEL_MONITOR
        monitor.settimeout(.2)
        print('MONITOR_READY read-only HCI0 sanitized metadata', flush=True)
        until = time.monotonic() + args.seconds
        while time.monotonic() < until:
            try:
                packet = monitor.recv(65535)
            except TimeoutError:
                continue
            sanitized = sanitized_packet(packet)
            if sanitized is not None:
                sanitized['monotonic_ns'] = time.monotonic_ns()
                record['records'].append(sanitized)
                if len(record['records']) >= 10000:
                    record['stopped_at_record_bound'] = True
                    break
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + '\n')
    print(f'MONITOR_CLOSED sanitized_records={len(record["records"])}', flush=True)


if __name__ == '__main__':
    main()
