"""Independent byte fixtures for redacted HCI2036/v1 and2037 metadata.

These tests open no devices. Fixtures follow Core5.4 Vol4 PartE7.8.53/54,
not the source helper's parameter encoder. Source-helper crosschecks are an
additional regression, not the fixture's provenance.
"""
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ble_hci_monitor import sanitized_packet
from ble_dumpcap_monitor import MonitorPcap
import ble_direct_hci_source as source


def command(opcode, payload):
    frame = struct.pack('<HB', opcode, len(payload)) + payload
    return struct.pack('<HHH', 2, 0, len(frame)) + frame


# handle1, props0, min=max32*625us, channel37, public Own/Peer,
# zero Peer_Address, policy0, no requested TX power, both LE1M,
# maxSkip0, SID0, scan notification0. Exactly25 bytes, not v2's27.
PRIMARY = bytes.fromhex('01 0000 200000 200000 01 00 00 000000000000 00 7f 01 00 01 00 00')
PRIMARY_EXPECTED = {
    'kind': 'advertising_command', 'hci_opcode_hex': '2036',
    'extended_parameters_wire_version': 1,
    'advertising_handle': 1, 'event_properties': 0,
    'interval_min_ms': 20, 'interval_max_ms': 20,
    'interval_min_625us_units': 32, 'interval_max_625us_units': 32,
    'primary_intervals_ignored_high_duty': False,
    'primary_channel_map': 1, 'own_address_type': 0, 'peer_address_type': 0,
    'peer_address_is_zero': True, 'advertising_filter_policy': 0,
    'requested_tx_power_dbm': None, 'tx_power_no_preference': True,
    'primary_phy': 1, 'secondary_max_skip': 0, 'secondary_phy': 1,
    'secondary_parameters_ignored_legacy': False,
    'advertising_sid': 0, 'scan_request_notification_enabled': False,
}


def changed(offset, value, size=1):
    p = bytearray(PRIMARY)
    p[offset:offset+size] = value.to_bytes(size, 'little')
    return bytes(p)


class ExtendedWireFieldsTests(unittest.TestCase):
    def test_primary_profile_full_independent_wire_fixture(self):
        self.assertEqual(len(PRIMARY), 25)
        self.assertEqual(sanitized_packet(command(0x2036, PRIMARY)), PRIMARY_EXPECTED)
        data = sanitized_packet(command(0x2037, bytes.fromhex('01030100')))
        self.assertEqual(data, {
            'kind': 'advertising_command', 'hci_opcode_hex': '2037',
            'advertising_handle': 1, 'advertising_data_length': 0,
            'fragment_operation': 3, 'fragmentation_preference': 1,
            'owned_manufacturer_ad_exact_match': False})

    def test_observed_fields_follow_actual_changed_bytes_not_constants(self):
        cases = [(0, 239, 'advertising_handle', 239),
                 (1, 0x40, 'event_properties', 0x40),
                 (6, 0x30, 'interval_max_625us_units', 48),
                 (9, 7, 'primary_channel_map', 7),
                 (10, 3, 'own_address_type', 3),
                 (11, 1, 'peer_address_type', 1),
                 (18, 3, 'advertising_filter_policy', 3),
                 (19, 0x81, 'requested_tx_power_dbm', -127),
                 (20, 3, 'primary_phy', 3),
                 (21, 255, 'secondary_max_skip', 255),
                 (22, 2, 'secondary_phy', 2),
                 (23, 15, 'advertising_sid', 15),
                 (24, 1, 'scan_request_notification_enabled', True)]
        for offset, value, key, expected in cases:
            with self.subTest(key=key):
                actual = sanitized_packet(command(0x2036, changed(offset, value)))
                self.assertIsNotNone(actual)
                self.assertEqual(actual[key], expected)
                self.assertNotEqual(actual, PRIMARY_EXPECTED)
        for low, high in [(32, 33), (0x123456, 0x123457), (0xffffff, 0xffffff)]:
            p = bytearray(PRIMARY)
            p[3:6], p[6:9] = low.to_bytes(3, 'little'), high.to_bytes(3, 'little')
            result = sanitized_packet(command(0x2036, bytes(p)))
            self.assertEqual(result['interval_min_ms'], low * .625)
            self.assertEqual(result['interval_max_ms'], high * .625)

    def test_address_bytes_are_discarded_without_hash_or_encoding(self):
        p = bytearray(PRIMARY)
        p[12:18] = b'SECRET'
        result = sanitized_packet(command(0x2036, bytes(p)))
        expected = dict(PRIMARY_EXPECTED, peer_address_is_zero=False)
        self.assertEqual(result, expected)
        # Two arbitrary nonzero addresses are indistinguishable in public data.
        p[12:18] = bytes.fromhex('123456789abc')
        self.assertEqual(sanitized_packet(command(0x2036, bytes(p))), result)
        for forbidden in ('SECRET', '534543524554', '123456789abc', 'sha256'):
            self.assertNotIn(forbidden, json.dumps(result))

    def test_exact_length_truncation_extra_bytes_and_v2_refused(self):
        for size in range(25):
            self.assertIsNone(sanitized_packet(command(0x2036, PRIMARY[:size])))
        for extra in (b'\0', b'\0\0', b'PRIVATE'):
            self.assertIsNone(sanitized_packet(command(0x2036, PRIMARY+extra)))
        self.assertIsNone(sanitized_packet(command(0x207f, PRIMARY+b'\0\0')))
        # Refuse transport-level truncation even when most new fields exist.
        self.assertIsNone(sanitized_packet(command(0x2036, PRIMARY)[:-1]))

    def test_reserved_values_maps_intervals_and_phy_are_refused(self):
        cases = [(0, 240), (9, 0), (9, 8), (9, 255), (10, 4), (11, 2),
                 (18, 4), (19, 0x80), (19, 21), (19, 126),
                 (20, 0), (20, 2), (20, 4), (22, 0), (22, 4),
                 (23, 16), (24, 2), (3, 31), (6, 31)]
        for offset, value in cases:
            with self.subTest(offset=offset, value=value):
                self.assertIsNone(sanitized_packet(command(0x2036, changed(offset, value))))
        for properties in (3, 8, 0x80, 0x100, 0x8000, 0xffff, 0x11, 0x50):
            self.assertIsNone(sanitized_packet(command(0x2036, changed(1, properties, 2))))
        p = bytearray(PRIMARY)
        p[3:6], p[6:9] = (33).to_bytes(3, 'little'), (32).to_bytes(3, 'little')
        self.assertIsNone(sanitized_packet(command(0x2036, bytes(p))))

    def test_power_boundary_and_no_preference_are_not_measured_power(self):
        for wire, expected in [(0x81, -127), (0xff, -1), (0, 0), (20, 20), (127, None)]:
            actual = sanitized_packet(command(0x2036, changed(19, wire)))
            self.assertEqual(actual['requested_tx_power_dbm'], expected)
            self.assertEqual(actual['tx_power_no_preference'], wire == 127)
            self.assertNotIn('selected_tx_power_dbm', actual)

    def test_extended_legacy_types_preserve_values_and_ignored_semantics(self):
        for props in (0x10, 0x12, 0x13, 0x15, 0x1d):
            p = bytearray(changed(1, props, 2))
            # Secondary fields are explicitly ignored for legacy types; don't
            # falsely reject an otherwise valid old command's unused PHY byte.
            p[22] = 0
            if props == 0x1d:
                p[3:9] = bytes(6)  # high-duty intervals explicitly ignored.
            actual = sanitized_packet(command(0x2036, bytes(p)))
            self.assertIsNotNone(actual)
            self.assertTrue(actual['secondary_parameters_ignored_legacy'])
            self.assertEqual(actual['primary_intervals_ignored_high_duty'], props == 0x1d)
            p[20] = 3
            self.assertIsNone(sanitized_packet(command(0x2036, bytes(p))))

    def test_fragment_preference_is_actual_byte_and_data_stays_redacted(self):
        marker = bytes.fromhex('0fffffff4553502d5344522d4556414c')
        for preference in (0, 1):
            for operation in range(4):
                payload = bytes([1, operation, preference, len(marker)])+marker
                result = sanitized_packet(command(0x2037, payload))
                self.assertEqual(result['fragmentation_preference'], preference)
                self.assertEqual(result['fragment_operation'], operation)
                self.assertEqual(result['owned_manufacturer_ad_exact_match'], True if operation == 3 else None)
                self.assertNotIn('455350', json.dumps(result))
        result = sanitized_packet(command(0x2037, b'\x01\x04\x00\x00'))
        self.assertIsNone(result['owned_manufacturer_ad_exact_match'])

    def test_data_reserved_fields_zero_fragment_and_overlength_refused(self):
        cases = [b'\xf0\x03\x01\x00', b'\x01\x05\x01\x00', b'\x01\x03\x02\x00',
                 b'\x01\x04\x01\x01x', b'\x01\x03\x01\x01', b'\x01\x03\x01\x00x']
        cases += [bytes([1, operation, 1, 0]) for operation in range(3)]
        cases += [bytes([1, 3, 1, 252])+bytes(252)]
        for payload in cases:
            with self.subTest(length=len(payload), prefix=payload[:4].hex()):
                # payload>255 can't fit a real HCI command length field;
                # exercise the bounded helper directly for this one case.
                if len(payload) > 255:
                    from ble_hci_monitor import extended_data_metadata
                    self.assertIsNone(extended_data_metadata(payload))
                else:
                    self.assertIsNone(sanitized_packet(command(0x2037, payload)))
        for length in range(4):
            self.assertIsNone(sanitized_packet(command(0x2037, bytes(length))))
        valid = bytes([239, 3, 0, 251])+bytes(251)
        self.assertEqual(sanitized_packet(command(0x2037, valid))['advertising_data_length'], 251)

    def test_controller_refusal_remains_refusal_with_invalid_request_discarded(self):
        self.assertIsNone(sanitized_packet(command(0x2036, changed(23, 16))))
        frame = bytes.fromhex('0e 05 01 3620 12 00')
        result = sanitized_packet(struct.pack('<HHH', 3, 0, len(frame))+frame)
        self.assertEqual(result, {'kind': 'advertising_command_complete',
                                 'hci_opcode_hex': '2036', 'status': 0x12})
        self.assertNotIn('profile_accepted', result)

    def test_independent_pcap_transport_preserves_full_zero_profile(self):
        global_header = struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65539, 254)
        records = []
        for opcode, payload in [(0x2036, PRIMARY), (0x2037, bytes.fromhex('01030100'))]:
            packet = struct.pack('>HH', 0, 2)+struct.pack('<HB', opcode, len(payload))+payload
            records.append(struct.pack('<IIII', 10, 100, len(packet), len(packet))+packet)
        parser = MonitorPcap()
        rows = []
        stream = global_header+b''.join(records)
        for offset in range(0, len(stream), 7):
            rows.extend(parser.feed(stream[offset:offset+7]))
        parser.finish()
        params = dict(rows[0]); params.pop('capture_timestamp_ns'); params.pop('monotonic_ns')
        self.assertEqual(params, PRIMARY_EXPECTED)
        self.assertEqual(rows[1]['fragmentation_preference'], 1)
        self.assertEqual(rows[1]['advertising_data_length'], 0)

    def test_source_encoder_crosscheck_old_and_new_profiles(self):
        self.assertEqual(source.parameters(20, handle=1, extended=True), PRIMARY)
        self.assertEqual(source.advertising_data(handle=1, zero_data=True), bytes.fromhex('01030100'))
        for interval in (20, 100):
            params = sanitized_packet(command(0x2036, source.parameters(interval)))
            self.assertEqual(params['event_properties'], 0x10)
            self.assertEqual(params['interval_min_ms'], interval)
            self.assertEqual(params['advertising_handle'], 239)
        data = sanitized_packet(command(0x2037, source.advertising_data()))
        self.assertTrue(data['owned_manufacturer_ad_exact_match'])
        self.assertEqual(data['fragmentation_preference'], 1)


if __name__ == '__main__':
    unittest.main()
