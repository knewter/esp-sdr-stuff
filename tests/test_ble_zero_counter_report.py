"""Metadata-only guards for the diagnostic; no device, RF or source operation."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from ble_zero_counter_report import analyze_segment, coverage, phase
from test_ble_counted_report import packet, receiver_fixture

SECOND = 1000000000


def episodes():
    return [dict(episode_id=f'zero-counter-{i+1:02d}', enable_sent_ns=(6+i*6)*SECOND,
                 guarded_start_ns=(6+i*6)*SECOND+100000000,
                 guarded_end_ns=(11+i*6)*SECOND-100000000,
                 source_closed_ns=(11+i*6)*SECOND) for i in range(10)]


class ZeroCounterReportTests(unittest.TestCase):
    def test_whole_response_guard_excludes_crossing_payload(self):
        schedule = episodes()
        self.assertEqual(phase(7*SECOND, 8*SECOND, schedule), 'zero-counter-01')
        self.assertEqual(phase(10*SECOND, 11*SECOND, schedule), 'control_boundary_excluded')
        self.assertEqual(phase(6*SECOND, 7*SECOND, schedule), 'control_boundary_excluded')
        self.assertEqual(phase(0, 5*SECOND, schedule), 'source_off_before')
        self.assertEqual(phase(12*SECOND-500000000, 12*SECOND-200000000, schedule),
                         'source_off_gap_after_zero-counter-01')

    def test_separate_tail_does_not_repair_original_schedule(self):
        schedule = episodes(); closed = schedule[-1]['source_closed_ns']
        main = [dict(command_start_ns=0, payload_received_ns=closed+8620000000)]
        tail = [dict(command_start_ns=closed+60*SECOND, payload_received_ns=closed+75*SECOND)]
        result = coverage(main, tail, schedule)
        self.assertFalse(result['original_tail_more_than_ten_seconds'])
        self.assertFalse(result['original_schedule_acceptance'])
        self.assertFalse(result['continuous_tail_requirement_repaired_by_extension'])
        self.assertAlmostEqual(result['supplemental_segment_gap_seconds'], 51.38)

    def test_failed_and_truncated_aa_candidates_remain_unowned(self):
        rows, _, decoded = receiver_fixture()
        decoded['captures'][1]['frames'] = [dict(status='truncated_packet', access_address_sample_offset=1000)]
        result = analyze_segment(rows, decoded, episodes(), 'main')
        self.assertEqual(result['complete_owned_packets'], [])
        self.assertEqual(result['phases']['zero-counter-01']['captures_with_aa_candidates'], 1)

    def test_type_and_full_window_guard_and_hypothesis_dedup(self):
        rows, _, decoded = receiver_fixture()
        decoded['captures'][1]['frames'] = [packet(1000), packet(1002)]
        result = analyze_segment(rows, decoded, episodes(), 'main')
        self.assertEqual(len(result['complete_owned_packets']), 1)
        rows, _, decoded = receiver_fixture()
        decoded['captures'][1]['frames'] = [packet(20)]
        decoded['captures'][2]['frames'] = [{**packet(), 'pdu_type': 0}]
        result = analyze_segment(rows, decoded, episodes(), 'main')
        self.assertEqual(result['complete_owned_packets'], [])
        self.assertEqual(len(result['excluded_crc_valid_owned_candidates']), 2)

    def test_physically_incompatible_owned_clusters_rejected(self):
        rows, _, decoded = receiver_fixture()
        decoded['captures'][1]['frames'] = [packet(1000), packet(7000)]
        with self.assertRaisesRegex(ValueError, 'multiple_owned_clusters'):
            analyze_segment(rows, decoded, episodes(), 'main')

    def test_undeclared_search_or_transport_failure_rejected(self):
        for mode in ('search', 'transport', 'missing_capture', 'period'):
            rows, _, decoded = receiver_fixture()
            if mode == 'search': decoded['blind_receiver_refinement'] = None
            elif mode == 'transport': rows[0]['crc_ok'] = False
            elif mode == 'missing_capture': decoded['captures'].pop()
            else: decoded['captures'][1]['frames'] = [{**packet(), 'samples_per_symbol_at_4msps': 4.04}]
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                analyze_segment(rows, decoded, episodes(), 'main')


if __name__ == '__main__': unittest.main()
