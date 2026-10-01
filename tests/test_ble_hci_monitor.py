"""Monitor parser must publish only selected control metadata."""
import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ble_hci_monitor import sanitized_packet


def command(opcode, payload, index=0):
    frame = struct.pack('<HB', opcode, len(payload)) + payload
    return struct.pack('<HHH', 2, index, len(frame)) + frame


class HCIMonitorTests(unittest.TestCase):
    def test_legacy_parameters_discard_peer_address(self):
        payload = struct.pack('<HHBBB', 0x800, 0x800, 3, 0, 0) + b'SECRET' + bytes([7, 0])
        result = sanitized_packet(command(0x2006, payload))
        self.assertEqual(result['interval_min_ms'], 1280)
        self.assertEqual(result['primary_channel_map'], 7)
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertEqual(len(result), 6)

    def test_extended_enable_count_and_termination(self):
        result = sanitized_packet(command(0x2039, bytes([1, 1, 2, 100, 0, 37])))
        self.assertEqual(result['sets'], [{'handle': 2, 'duration_10ms_units': 100, 'maximum_extended_advertising_events': 37}])
        data = bytes([0x3e, 6, 0x12, 0, 2, 0xff, 0xff, 37])
        result = sanitized_packet(struct.pack('<HHH', 3, 0, len(data)) + data)
        self.assertEqual(result['controller_reported_completed_extended_advertising_events'], 37)
        self.assertNotIn('connection_handle', result)

    def test_foreign_data_other_controller_and_malformed_discarded(self):
        self.assertIsNone(sanitized_packet(command(0x2008, b'PRIVATE-ADVERTISEMENT')))
        self.assertIsNone(sanitized_packet(command(0x200a, bytes([1]), index=1)))
        self.assertIsNone(sanitized_packet(command(0x2039, b'')))
        self.assertIsNone(sanitized_packet(command(0x2039, bytes([1, 8]))))
        self.assertIsNone(sanitized_packet(b'bad'))
        self.assertIsNone(sanitized_packet(command(0x200a, bytes([1]))[:-1]))

    def test_owned_controller_data_is_matched_then_discarded(self):
        marker = bytes.fromhex('0fffffff4553502d5344522d4556414c')
        legacy = bytes([len(marker)]) + marker + bytes(31 - len(marker))
        result = sanitized_packet(command(0x2008, legacy))
        self.assertTrue(result['owned_manufacturer_ad_exact_match'])
        self.assertNotIn('455350', json.dumps(result))
        foreign = bytes([7]) + b'\x06\xffABCDE' + bytes(24)
        self.assertFalse(sanitized_packet(command(0x2008, foreign))['owned_manufacturer_ad_exact_match'])
        extended = bytes([2, 3, 1, len(marker)]) + marker
        self.assertTrue(sanitized_packet(command(0x2037, extended))['owned_manufacturer_ad_exact_match'])
        extended = bytes([2, 1, 1, len(marker)]) + marker
        self.assertIsNone(sanitized_packet(command(0x2037, extended))['owned_manufacturer_ad_exact_match'])


if __name__ == '__main__':
    unittest.main()
