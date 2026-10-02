"""Synthetic pcap transport tests; no live Bluetooth or network capture."""
import contextlib
from unittest.mock import patch
import io
import json
from pathlib import Path
import struct
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from ble_dumpcap_monitor import MonitorPcap, PcapError, capture_command, dumpcap_command


def global_header(order='<', nano=False, linktype=254, snaplen=65539):
    magic = 0xa1b23c4d if nano else 0xa1b2c3d4
    return struct.pack(order+'IHHIIII', magic, 2, 4, 0, 0, snaplen, linktype)


def packet_record(packet, order='<', fraction=123, original=None):
    return struct.pack(order+'IIII', 10, fraction, len(packet), len(packet) if original is None else original)+packet


def hci_command(opcode, payload, adapter=0):
    # DLT254 pseudoheader stays big-endian regardless of pcap byte order.
    return struct.pack('>HH', adapter, 2)+struct.pack('<HB', opcode, len(payload))+payload


class DumpcapMonitorTests(unittest.TestCase):
    def test_all_pcap_orders_timestamp_units_and_fragmented_pipe(self):
        for order in ('<', '>'):
            for nano in (False, True):
                with self.subTest(order=order, nano=nano):
                    raw = global_header(order, nano)+packet_record(hci_command(0x200a, b'\1'), order)
                    parser = MonitorPcap()
                    rows = []
                    for byte in raw:
                        rows.extend(parser.feed(bytes([byte])))
                    parser.finish()
                    self.assertEqual(rows[0]['hci_opcode_hex'], '200a')
                    self.assertTrue(rows[0]['enabled'])
                    self.assertEqual(rows[0]['capture_timestamp_ns'], 10000000000+123*(1 if nano else 1000))

    def test_monitor_header_conversion_redacts_all_private_data(self):
        params = struct.pack('<HHBBB', 160, 160, 3, 0, 0)+b'SECRET'+bytes([7, 0])
        new_index = struct.pack('>HH', 0, 0)+b'PRIVATE-ADDRESS-NAME'
        foreign = hci_command(0x200a, b'\1', adapter=1)
        malformed_hci = hci_command(0x2008, b'PRIVATE-ADVERTISING')
        event = struct.pack('>HH', 0, 3)+bytes([0x3e, 6, 0x12, 0, 2, 0xab, 0xcd, 37])
        stream = global_header()+b''.join(packet_record(p) for p in [new_index, foreign, malformed_hci, hci_command(0x2006, params), event])
        parser = MonitorPcap()
        rows = parser.feed(stream)
        parser.finish()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['interval_min_ms'], 100)
        self.assertEqual(rows[1]['controller_reported_completed_extended_advertising_events'], 37)
        for secret in ('SECRET', 'PRIVATE', 'connection_handle', 'adapter_id'):
            self.assertNotIn(secret, json.dumps(rows))

    def test_owned_marker_match_then_discard_bytes(self):
        marker = bytes.fromhex('0fffffff4553502d5344522d4556414c')
        payload = bytes([len(marker)])+marker+bytes(31-len(marker))
        rows = MonitorPcap().feed(global_header()+packet_record(hci_command(0x2008, payload)))
        self.assertTrue(rows[0]['owned_manufacturer_ad_exact_match'])
        self.assertNotIn('ESP-SDR-EVAL', json.dumps(rows))
        self.assertNotIn('455350', json.dumps(rows))

    def test_rejects_pcapng_wrong_dlt_version_and_oversized_lengths(self):
        cases = [b'\x0a\x0d\x0d\x0a'+bytes(20), global_header(linktype=201),
                 global_header(snaplen=262144), global_header()+struct.pack('<IIII', 1, 0, 65540, 65540),
                 global_header()+struct.pack('<IIII', 1, 0, 8, 7),
                 global_header()+struct.pack('<IIII', 1, 1000000, 8, 8)]
        for case in cases:
            with self.subTest(case=case[:8].hex()), self.assertRaises(PcapError):
                MonitorPcap().feed(case)
        header = bytearray(global_header())
        header[4:6] = struct.pack('<H', 3)
        with self.assertRaises(PcapError):
            MonitorPcap().feed(header)

    def test_truncated_packet_is_discarded_without_false_acceptance(self):
        packet = hci_command(0x200a, b'\1')
        parser = MonitorPcap()
        rows = parser.feed(global_header()+packet_record(packet, original=len(packet)+1))
        parser.finish()
        self.assertEqual(rows, [])
        self.assertEqual(parser.truncated_packets, 1)

    def test_partial_eof_short_header_and_memory_bound(self):
        for data in [b'', global_header()[:-1], global_header()+packet_record(hci_command(0x200a, b'\1'))[:-1]]:
            parser = MonitorPcap()
            parser.feed(data)
            with self.assertRaises(PcapError):
                parser.finish()
        with self.assertRaises(PcapError):
            MonitorPcap().feed(global_header()+packet_record(b'bad'))
        with self.assertRaises(PcapError):
            MonitorPcap().feed(bytes(65537))

    def test_command_has_stdout_single_interface_and_capture_bound(self):
        with patch.dict("os.environ", {"DUMPCAP": "/test/bin/dumpcap"}):
            args = dumpcap_command(12.5)
        self.assertEqual(args[0], "/test/bin/dumpcap")
        self.assertEqual(args[args.index('-w')+1], '-')
        self.assertEqual(args[args.index('-i')+1], 'bluetooth-monitor')
        self.assertIn('-P', args)
        self.assertEqual(args[args.index('-a')+1], 'duration:12.5')
        self.assertNotIn('--log-file', args)

    def producer(self, data, tail=''):
        return [sys.executable, '-c', 'import sys,time; sys.stdout.buffer.write('+repr(data)+'); sys.stdout.flush(); '+tail]

    def test_synthetic_process_success_privacy_and_cleanup(self):
        raw = global_header()+packet_record(hci_command(0x200a, b'\1'))
        with contextlib.redirect_stdout(io.StringIO()):
            result = capture_command(self.producer(raw, "sys.stderr.write('PRIVATE-STDERR')"), 1, grace=.1)
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['producer_reaped'])
        self.assertEqual(len(result['records']), 1)
        self.assertIsNone(result['independently_observed_air_emission_count'])
        self.assertFalse(result['raw_capture_written_to_disk'])
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_silent_producer_deadline_and_record_bound_reap_child(self):
        with contextlib.redirect_stdout(io.StringIO()):
            started = time.monotonic()
            deadline = capture_command(self.producer(global_header(), 'time.sleep(30)'), .1, grace=.1)
            raw = global_header()+packet_record(hci_command(0x200a, b'\1'))*3
            bound = capture_command(self.producer(raw, 'time.sleep(30)'), 1, grace=.1, record_limit=2)
        self.assertLess(time.monotonic()-started, 3)
        self.assertEqual(deadline['status'], 'host_deadline')
        self.assertTrue(deadline['producer_reaped'])
        self.assertEqual(bound['status'], 'record_bound')
        self.assertEqual(len(bound['records']), 2)
        self.assertTrue(bound['producer_reaped'])

    def test_malformed_or_failed_producer_does_not_claim_completion(self):
        with contextlib.redirect_stdout(io.StringIO()):
            bad = capture_command(self.producer(b'PRIVATE'+bytes(24)), 1, grace=.1)
            failed = capture_command(self.producer(global_header(), 'sys.exit(7)'), 1, grace=.1)
        self.assertEqual(bad['status'], 'invalid_pcap')
        self.assertTrue(bad['producer_reaped'])
        self.assertNotIn('PRIVATE', json.dumps(bad))
        self.assertEqual(failed['status'], 'producer_failed')
        self.assertEqual(failed['producer_returncode'], 7)


if __name__ == '__main__':
    unittest.main()
