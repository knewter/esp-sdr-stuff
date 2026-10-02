"""Metadata-only guards for the diagnostic; no device, RF or source operation."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from ble_zero_counter_report import SOURCE_SHA256, analyze_segment, check_episode, coverage, phase, validate_episode_schedule
from test_ble_counted_report import monitor_fixture, packet as base_packet, receiver_fixture, source_fixture

SECOND = 1000000000


def packet(offset=1000):
    return {**base_packet(offset), 'nominal_packet_start_sample': offset-128,
            'nominal_packet_end_sample': offset-128+4096,
            'complete_preamble_and_pdu_crc_within_capture_nominal': offset >= 128 and offset+3968 <= 16380}


def episodes():
    return [dict(episode_id=f'zero-counter-{i+1:02d}', enable_sent_ns=(6+i*6)*SECOND,
                 guarded_start_ns=(6+i*6)*SECOND+100000000,
                 guarded_end_ns=(11+i*6)*SECOND-100000000,
                 source_closed_ns=(11+i*6)*SECOND) for i in range(10)]


def diagnostic_fixture():
    records = source_fixture()
    for row in records:
        if 'advertising_handle' in row: row['advertising_handle'] = 1
        if row['kind'] == 'configuration_requested':
            row.update(duration_10ms_units=500, duration_diagnostic_requested=True, handle_diagnostic_requested=True,
                       script_sha256=SOURCE_SHA256)
        if row['kind'] == 'termination_observed':
            row.update(status=60, controller_reported_completed_extended_advertising_events=0)
        if row['kind'] == 'source_enabled': row['duration_10ms_units'] = 500
        if row['kind'] == 'source_closed':
            row.update(status='trial_failed', error_code='termination_status_or_count_mismatch',
                       controller_completed_count_verified=False)
    enable_sent = next(r for r in records if r['kind'] == 'command_sent' and r['step'] == 'enable')
    records.insert(records.index(enable_sent), dict(kind='source_ready', start_delay_s=0,
                                                   monotonic_ns=enable_sent['monotonic_ns']-1))
    monitor = monitor_fixture()['records']
    native_commands = [r for r in records if r['kind'] == 'command_sent']
    native_acks = [r for r in records if r['kind'] == 'command_complete']
    native_term = next(r for r in records if r['kind'] == 'termination_observed')
    for index, row in enumerate(monitor):
        if 'advertising_handle' in row: row['advertising_handle'] = 1
        if row['kind'] == 'controller_advertising_set_terminated':
            row.update(status=60, controller_reported_completed_extended_advertising_events=0,
                       monotonic_ns=native_term['monotonic_ns'])
        elif row['kind'] == 'advertising_command':
            offset = (0, 2, 4, 7, 9).index(index); row['monotonic_ns'] = native_commands[offset]['monotonic_ns']
            if 'sets' in row:
                row['sets'][0]['handle'] = 1
                if row['enabled']: row['sets'][0]['duration_10ms_units'] = 500
        else:
            offset = (1, 3, 5, 8, 10).index(index); row['monotonic_ns'] = native_acks[offset]['monotonic_ns']
    summary = next(r for r in records if r['kind'] == 'source_closed')
    return records, monitor, summary


class ZeroCounterReportTests(unittest.TestCase):
    def test_native_and_monitor_zero_counter_are_diagnostic_not_success(self):
        native, monitor, summary = diagnostic_fixture()
        receipt = check_episode(native, monitor, summary)
        self.assertEqual(receipt['original_source_status'], 'trial_failed')
        self.assertEqual(receipt['source_returncode'], 2)
        self.assertEqual(receipt['controller_reported_completed_events'], 0)
        self.assertIsNone(receipt['actual_rf_emissions'])
        self.assertTrue(receipt['native_and_monitor_zero_counter_match'])

    def test_source_monitor_counter_handle_data_and_cleanup_must_match(self):
        for mode in ('source_handle', 'max_zero', 'native_count', 'monitor_count', 'monitor_handle',
                     'marker', 'cleanup', 'missing_term', 'summary_success', 'enabled_duration', 'request_duration', 'source_hash'):
            native, monitor, summary = diagnostic_fixture()
            if mode == 'source_handle': native[0]['advertising_handle'] = 239
            elif mode == 'max_zero': native[0]['max_extended_advertising_events'] = 0
            elif mode == 'native_count': next(r for r in native if r['kind'] == 'termination_observed')['controller_reported_completed_extended_advertising_events'] = 123
            elif mode == 'monitor_count': monitor[6]['controller_reported_completed_extended_advertising_events'] = 123
            elif mode == 'monitor_handle': monitor[6]['advertising_handle'] = 239
            elif mode == 'marker': monitor[2]['owned_manufacturer_ad_exact_match'] = False
            elif mode == 'cleanup': monitor[-1]['status'] = 12
            elif mode == 'missing_term': monitor.pop(6)
            elif mode == 'enabled_duration': next(r for r in native if r['kind'] == 'source_enabled')['duration_10ms_units'] = 0
            elif mode == 'request_duration': next(r for r in native if r.get('step') == 'enable' and r['kind'] == 'command_sent')['duration_10ms_units'] = 0
            elif mode == 'source_hash': native[0]['script_sha256'] = 'arbitrary'
            else: summary['status'] = 'controller_count_verified'
            with self.subTest(mode=mode), self.assertRaises(ValueError): check_episode(native, monitor, summary)

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

    def test_episode_order_off_gaps_and_baseline_enforced(self):
        self.assertEqual(validate_episode_schedule(episodes()), [1]*9)
        for mode in ('overlap', 'short_gap', 'reorder'):
            schedule = episodes()
            if mode == 'overlap': schedule[1]['enable_sent_ns'] = schedule[0]['source_closed_ns']-1
            elif mode == 'short_gap': schedule[1]['enable_sent_ns'] -= 1
            else: schedule[0], schedule[1] = schedule[1], schedule[0]
            with self.subTest(mode=mode), self.assertRaises(ValueError): validate_episode_schedule(schedule)
        schedule = episodes(); closed = schedule[-1]['source_closed_ns']
        main = [dict(command_start_ns=2*SECOND, payload_received_ns=closed+8*SECOND)]
        tail = [dict(command_start_ns=closed+60*SECOND, payload_received_ns=closed+75*SECOND)]
        with self.assertRaisesRegex(ValueError, 'baseline_before_enable_short'): coverage(main, tail, schedule)

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
        for index in (0, 1, 3):
            rows, _, decoded = receiver_fixture()
            if index == 3:
                rows[index]['command_start_ns'] = 11*SECOND
                rows[index]['header_received_ns'] = 11*SECOND+10000000
                rows[index]['payload_received_ns'] = 11*SECOND+30000000
            decoded['captures'][index]['frames'] = [packet(1000), packet(7000)]
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'multiple_owned_clusters'):
                analyze_segment(rows, decoded, episodes(), 'main')

    def test_explicit_complete_packet_proof_metadata_required(self):
        for mode in ('flag_missing', 'flag_false', 'begin_missing', 'end_missing', 'bounds_infinite', 'bounds_wrong'):
            rows, _, decoded = receiver_fixture(); frame = packet()
            if mode == 'flag_missing': del frame['complete_preamble_and_pdu_crc_within_capture_nominal']
            elif mode == 'flag_false': frame['complete_preamble_and_pdu_crc_within_capture_nominal'] = False
            elif mode == 'begin_missing': del frame['nominal_packet_start_sample']
            elif mode == 'end_missing': del frame['nominal_packet_end_sample']
            elif mode == 'bounds_infinite': frame['nominal_packet_end_sample'] = float('inf')
            else: frame['nominal_packet_end_sample'] += 16
            decoded['captures'][1]['frames'] = [frame]
            result = analyze_segment(rows, decoded, episodes(), 'main')
            with self.subTest(mode=mode): self.assertEqual(result['complete_owned_packets'], [])
        for mode in ('hash_missing', 'hash_invalid', 'refined_period_missing', 'period_nan', 'coarse_period'):
            rows, _, decoded = receiver_fixture(); frame = packet()
            if mode == 'hash_missing': del frame['pdu_sha256']
            elif mode == 'hash_invalid': frame['pdu_sha256'] = 'z'*64
            elif mode == 'refined_period_missing': frame['refined'] = True
            elif mode == 'coarse_period': frame['samples_per_symbol_at_4msps'] = 4.02
            else: frame['samples_per_symbol_at_4msps'] = float('nan')
            decoded['captures'][1]['frames'] = [frame]
            with self.subTest(mode=mode), self.assertRaises(ValueError):
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
