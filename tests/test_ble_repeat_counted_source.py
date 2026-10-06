"""Repeated counted source cycle/cleanup tests, using no hardware."""
from collections import deque
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from ble_direct_hci_source import Source
from ble_repeat_counted_source import run_cycles, validate_cycles, channel_parameters
from ble_repeat_source_container import source_command


def complete(opcode, status=0):
    body = bytes([1])+struct.pack('<H', opcode)+bytes([status])
    if opcode == 0x2036:
        body += bytes([4])
    return bytes([4, 0x0e, len(body)])+body


def terminated(status=0x43, count=255, handle=1):
    return bytes([4, 0x3e, 6, 0x12, status, handle, 0xff, 0xff, count])


class FakeSocket:
    def __init__(self, terminations=None):
        self.sent = []
        self.pending = deque()
        self.terminations = deque(terminations or [])

    def settimeout(self, value):
        pass

    def send(self, frame):
        self.sent.append(frame)
        opcode = struct.unpack_from('<H', frame, 1)[0]
        self.pending.append(complete(opcode))
        if opcode == 0x2039 and frame[4] == 1 and self.terminations:
            self.pending.append(self.terminations.popleft())
        return len(frame)

    def recv(self, size):
        if self.pending:
            return self.pending.popleft()
        raise TimeoutError()


def opcodes(sock):
    return [(struct.unpack_from('<H', f, 1)[0], f[4] if f[1:3] == b'\x39\x20' else None) for f in sock.sent]


class RepeatCycles(unittest.TestCase):
    def run_source(self, sock, cycles, cycle_timeout_s=None):
        records = []
        with patch('time.sleep'):
            summary = run_cycles(Source(sock, records.append, command_timeout=.05), cycles, 0, cycle_timeout_s)
        return summary, records

    def test_all_cycles_counted_then_scoped_cleanup(self):
        sock = FakeSocket([terminated()]*3)
        summary, records = self.run_source(sock, 3)
        self.assertEqual(summary['status'], 'all_cycles_counted')
        self.assertEqual(summary['controller_counted_events_total'], 765)
        self.assertTrue(summary['cleanup_success'])
        self.assertEqual(opcodes(sock), [(0x2036, None), (0x2037, None), (0x2039, 1), (0x2039, 1),
                                         (0x2039, 1), (0x2039, 0), (0x203c, None)])
        enable_frame = sock.sent[2]
        self.assertEqual(enable_frame[4:], bytes([1, 1, 1, 0, 0, 255]))
        self.assertEqual(sum(r['kind'] == 'cycle_verified' for r in records), 3)

    def test_short_count_stops_and_still_cleans_up(self):
        sock = FakeSocket([terminated(), terminated(count=254), terminated()])
        summary, _ = self.run_source(sock, 3)
        self.assertEqual(summary['status'], 'trial_failed')
        self.assertEqual(summary['cycles_verified'], 1)
        self.assertEqual(summary['failed_cycle'], 1)
        self.assertTrue(summary['cleanup_success'])

    def test_duration_status_is_not_counted(self):
        summary, _ = self.run_source(FakeSocket([terminated(status=0x3c, count=0)]), 1)
        self.assertEqual(summary['status'], 'trial_failed')
        self.assertEqual(summary['controller_counted_events_total'], 0)

    def test_missing_termination_times_out(self):
        summary, _ = self.run_source(FakeSocket([]), 1, cycle_timeout_s=.05)
        self.assertEqual(summary['status'], 'trial_failed')
        self.assertEqual(summary['error_code'], 'event_timeout')

    def test_channel_selects_only_the_primary_map_byte(self):
        base = channel_parameters(37)
        for channel, bit in ((38, 2), (39, 4)):
            frame = channel_parameters(channel)
            self.assertEqual(frame[9], bit)
            self.assertEqual(frame[:9]+frame[10:], base[:9]+base[10:])
        with self.assertRaises(ValueError):
            channel_parameters(36)

    def test_cycles_use_requested_channel(self):
        sock = FakeSocket([terminated()])
        records = []
        with patch('time.sleep'):
            summary = run_cycles(Source(sock, records.append, command_timeout=.05), 1, 0, channel=39)
        self.assertEqual(summary['primary_channel'], 39)
        self.assertEqual(sock.sent[0][4+9], 4)

    def test_cycle_bounds(self):
        for bad in (0, 401, 1.5, True):
            with self.assertRaises(ValueError):
                validate_cycles(bad)
        self.assertEqual(validate_cycles(400), 400)

    def test_container_command_is_scoped(self):
        command = source_command('esp-sdr-ble-source-'+'0'*32, 'sha256:'+'1'*64,
                                 '/nix/store/x-python3/bin/python3', ['--cycles', '2'])
        self.assertIn('NET_RAW', command)
        self.assertIn('--read-only', command)
        self.assertEqual(command[-3:], ['/app/ble_repeat_counted_source.py', '--cycles', '2'])
        with self.assertRaises(SystemExit):
            source_command('esp-sdr-ble-source-'+'0'*32, 'sha256:'+'1'*64,
                           '/nix/store/x-python3/bin/python3', ['--cycles', '0'])


if __name__ == '__main__':
    unittest.main()
