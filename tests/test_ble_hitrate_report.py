"""Synthetic join/classification tests for the hit-rate report; no hardware."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from ble_hitrate_report import classify, merge, poisson_interval, report

MS = 1_000_000


def cycle(start_ms, end_ms, status=0x43, count=255):
    return [{'kind': 'command_result', 'step': 'enable', 'status': 0, 'monotonic_ns': start_ms*MS},
            {'kind': 'termination_observed', 'status': status,
             'controller_reported_completed_extended_advertising_events': count, 'monotonic_ns': end_ms*MS}]


def row(attempt, start_ms, status='ok'):
    return {'status': status, 'rate_hz': '16000000', 'bits_per_component': '8', 'attempt': str(attempt),
            'command_start_relative_ms': str(start_ms), 'header_received_relative_ms': str(start_ms+8),
            'nominal_rf_window_us': '1023.75'}


def frame(complete=True):
    return {'status': 'valid_owned_primary', 'packet_duration_us': 200,
            'complete_preamble_and_pdu_crc_within_capture_nominal': complete}


class HitRate(unittest.TestCase):
    def test_merge_and_classify(self):
        merged = merge([{'start_ns': 0, 'end_ns': 100*MS}, {'start_ns': 104*MS, 'end_ns': 200*MS}])
        self.assertEqual(merged, [[0, 200*MS]])
        self.assertEqual(classify((50*MS, 60*MS), merged, 10*MS), 'on')
        self.assertEqual(classify((195*MS, 199*MS), merged, 10*MS), 'boundary')
        self.assertEqual(classify((300*MS, 310*MS), merged, 10*MS), 'off')

    def test_report_counts_and_expectation(self):
        source = cycle(1000, 7350)+cycle(7354, 13704)
        rows = [row(0, 100), row(1, 2000), row(2, 5000), row(3, 9000), row(4, 20000), row(5, 3000, 'error')]
        decode = {'captures': [{'capture_filename': f'iq-16000000-8-{i:04d}.bin',
                                'frames': [frame()] if i in (1, 3) else ([frame(False)] if i == 4 else [])}
                               for i in range(6)]}
        out = report({'series_start_monotonic_ns': 0}, rows, source, decode, guard_ms=100)
        self.assertEqual(out['controller_counted_events'], 510)
        self.assertEqual((out['captures_on'], out['captures_off'], out['captures_boundary_or_failed']), (3, 2, 1))
        self.assertEqual(out['on_owned_complete_frames'], 2)
        self.assertEqual(out['off_owned_primary_frames'], 1)
        expected = 3*(1023.75-200)*1e-6/(6.35/254)
        self.assertAlmostEqual(out['expected_complete_owned_in_on_windows'], expected, places=6)
        self.assertAlmostEqual(out['detection_efficiency'], 2/expected)

    def test_uncounted_cycle_contributes_no_events(self):
        out = report({'series_start_monotonic_ns': 0}, [row(0, 2000)], cycle(1000, 7350)+cycle(7354, 9000, 0x3c, 0),
                     {'captures': [{'capture_filename': 'iq-16000000-8-0000.bin', 'frames': []}]})
        self.assertEqual(out['controller_counted_events'], 255)
        self.assertEqual(out['source_cycles_counted'], 1)

    def test_poisson_interval_brackets(self):
        low, high = poisson_interval(10)
        self.assertLess(low, 10)
        self.assertGreater(high, 10)
        self.assertEqual(poisson_interval(0)[0], 0)


if __name__ == '__main__':
    unittest.main()
