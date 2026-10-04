#!/usr/bin/env python3
"""Read-only, bounded HCI0 advertising-control monitor with strict redaction.

Never sends HCI commands. Discards addresses, advertising bytes, names, foreign
traffic and all unspecified fields before writing metadata. Controller event
counts are explicitly distinguished from independently observed RF emissions.
"""
import argparse
import ctypes
import json
from pathlib import Path
import socket
import struct
import sys
import time

ADV_OPCODES = {0x2006, 0x2008, 0x200A, 0x2036, 0x2037, 0x2039, 0x203c}
OWNED_MARKER_AD = bytes.fromhex('0fffffff4553502d5344522d4556414c')
AF_BLUETOOTH_LINUX = 31  # Linux socket ABI, independent of CPython build flags.
HCI_CHANNEL_MONITOR = 2  # Linux include/net/bluetooth/hci_sock.h; CONTROL is3.


def monitor_sockaddr():
    return struct.pack('=HHH', AF_BLUETOOTH_LINUX, 0xffff, HCI_CHANNEL_MONITOR)


def owned_ad_match(data):
    offset = 0
    while offset < len(data):
        length = data[offset]
        if length == 0 or offset + length + 1 > len(data):
            break
        if data[offset:offset + length + 1] == OWNED_MARKER_AD:
            return True
        offset += length + 1
    return False


def bind_monitor(monitor):
    # CPython's HCI tuple converter does not populate hci_channel. An apparent
    # bind((device, 3)) can silently bind RAW instead of MONITOR on this host.
    # Pass Linux sockaddr_hci explicitly; no command is sent by this call.
    address = ctypes.create_string_buffer(monitor_sockaddr())
    libc = ctypes.CDLL(None, use_errno=True)
    libc.bind.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_uint]
    libc.bind.restype = ctypes.c_int
    if libc.bind(monitor.fileno(), address, 6) != 0:
        error = ctypes.get_errno()
        raise OSError(error, 'Cannot open the explicit read-only HCI monitor channel')


def extended_parameters_metadata(payload):
    """Decode opcode2036's exact v1 wire layout; never retain Peer_Address.

    Core5.4 Vol4 PartE7.8.53/Table7.2 defines this supported envelope.
    Later decision-advertising properties and opcode207f/v2 are outside it.
    These are requested control values, not observed PHY or radiated power.
    """
    if len(payload) != 25:
        return None
    handle, properties, low_bytes, high_bytes, channels, own_type, peer_type, peer, policy, power, primary, skip, secondary, sid, notify = struct.unpack(
        '<BH3s3sBBB6sBbBBBBB', payload)
    low = int.from_bytes(low_bytes, 'little')
    high = int.from_bytes(high_bytes, 'little')
    legacy = bool(properties & 0x10)
    high_duty = properties == 0x1d
    if (handle > 0xef or properties & ~0x7f or
            (legacy and properties not in (0x10, 0x12, 0x13, 0x15, 0x1d)) or
            (not legacy and (properties & 3 == 3 or properties & 8)) or
            (not high_duty and not 0x20 <= low <= high <= 0xffffff) or
            not 1 <= channels <= 7 or own_type > 3 or peer_type > 1 or
            policy > 3 or (power != 127 and not -127 <= power <= 20) or
            primary not in (1, 3) or (legacy and primary != 1) or
            (not legacy and secondary not in (1, 2, 3)) or
            sid > 15 or notify > 1):
        return None
    return {
        'extended_parameters_wire_version': 1,
        'advertising_handle': handle, 'event_properties': properties,
        'interval_min_ms': low * .625, 'interval_max_ms': high * .625,
        'interval_min_625us_units': low, 'interval_max_625us_units': high,
        'primary_intervals_ignored_high_duty': high_duty,
        'primary_channel_map': channels, 'own_address_type': own_type,
        'peer_address_type': peer_type,
        # A boolean can verify the deliberately zero, unused peer field in
        # the undirected source profile without publishing an address/hash.
        'peer_address_is_zero': peer == bytes(6),
        'advertising_filter_policy': policy,
        'requested_tx_power_dbm': None if power == 127 else power,
        'tx_power_no_preference': power == 127,
        'primary_phy': primary, 'secondary_max_skip': skip,
        'secondary_phy': secondary, 'secondary_parameters_ignored_legacy': legacy,
        'advertising_sid': sid, 'scan_request_notification_enabled': bool(notify),
    }


def extended_data_metadata(payload):
    """Core5.4 Vol4 PartE7.8.54; fragment data stays redacted/unassembled."""
    if not 4 <= len(payload) <= 255:
        return None
    handle, operation, preference, length = payload[:4]
    if (handle > 0xef or operation > 4 or preference > 1 or length > 251 or
            len(payload) != 4 + length or
            (operation == 4 and length != 0) or
            (operation not in (3, 4) and length == 0)):
        return None
    return {
        'advertising_handle': handle, 'advertising_data_length': length,
        'fragment_operation': operation, 'fragmentation_preference': preference,
        'owned_manufacturer_ad_exact_match': owned_ad_match(payload[4:]) if operation == 3 else None,
    }


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
        elif opcode == 0x2008 and len(payload) == 32 and payload[0] <= 31:
            result.update(advertising_data_length=payload[0],
                          owned_manufacturer_ad_exact_match=owned_ad_match(payload[1:1 + payload[0]]))
        elif opcode in (0x2036, 0x2037):
            metadata = (extended_parameters_metadata(payload) if opcode == 0x2036
                        else extended_data_metadata(payload))
            if metadata is None:
                return None
            result.update(metadata)
        elif opcode == 0x203c and len(payload) == 1:
            result['advertising_handle'] = payload[0]
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
    if sys.platform != 'linux' or not all(hasattr(socket, name) for name in ('AF_BLUETOOTH', 'BTPROTO_HCI')):
        parser.error('Live monitoring requires Linux and a Python build with Bluetooth socket support')
    record = {'schema': 1, 'kind': 'read-only sanitized HCI0 advertising control',
              'hci_channel':HCI_CHANNEL_MONITOR,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'independently_observed_air_emission_count': None, 'records': [],
              'packet_counts_by_monitor_kind': {},
              'limitations': 'HCI commands and controller-reported events are control-plane evidence. No independent RF emission counter. Unknown socket loss; unrelated traffic and addresses discarded before storage.'}
    with socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI) as monitor:
        try:
            bind_monitor(monitor)
        except OSError as error:
            record['status']='monitor_channel_bind_failed'
            record['bind_error_errno']=error.errno
            record['bind_error_kind']=type(error).__name__
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(record,indent=2)+'\n')
            print(f'MONITOR_UNAVAILABLE channel={HCI_CHANNEL_MONITOR} errno={error.errno}',flush=True)
            raise SystemExit(2)
        monitor.settimeout(.2)
        print('MONITOR_READY read-only HCI0 sanitized metadata', flush=True)
        until = time.monotonic() + args.seconds
        while time.monotonic() < until:
            try:
                packet = monitor.recv(65535)
            except TimeoutError:
                continue
            if len(packet) >= 6:
                kind = struct.unpack_from('<H', packet)[0]
                key = str(kind)
                record['packet_counts_by_monitor_kind'][key] = record['packet_counts_by_monitor_kind'].get(key, 0) + 1
            sanitized = sanitized_packet(packet)
            if sanitized is not None:
                sanitized['monotonic_ns'] = time.monotonic_ns()
                record['records'].append(sanitized)
                if len(record['records']) >= 10000:
                    record['stopped_at_record_bound'] = True
                    break
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record['status']='completed'
    args.output.write_text(json.dumps(record, indent=2) + '\n')
    print(f'MONITOR_CLOSED sanitized_records={len(record["records"])}', flush=True)


if __name__ == '__main__':
    main()
