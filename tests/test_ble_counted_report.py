"""Counted-trial accounting regressions, synthetic metadata only; no hardware."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from ble_counted_report import EXPECTED_REFINEMENT, MARKER, STEPS, aggregate, analyze_receiver, validate_monitor, validate_source, verify_private_waveforms

SECOND = 1000000000


def source_fixture():
    rows = []; now = 6*SECOND
    def add(kind, **fields):
        nonlocal now
        now += 1000000
        row = {'kind': kind, 'monotonic_ns': now, **fields}; rows.append(row); return row
    add('configuration_requested', advertising_handle=239, event_properties=16, primary_channel_map=1,
        primary_phy=1, secondary_phy=1, advertising_data_length=16, owned_manufacturer_ad_exact_match=True,
        duration_10ms_units=0, max_extended_advertising_events=255, interval_ms=20, script_sha256='a'*64)
    for step, opcode in STEPS:
        if step == 'cleanup_disable':
            now += 7*SECOND
            term = add('termination_observed', advertising_handle=239, status=67,
                       controller_reported_completed_extended_advertising_events=255,
                       observed_after_enable_command_sent=True)
        add('command_sent', step=step, hci_opcode_hex=opcode, advertising_handle=239)
        add('command_complete', hci_opcode_hex=opcode, status=0)
        add('command_result', step=step, hci_opcode_hex=opcode, status=0)
        if step == 'enable':
            add('source_enabled', advertising_handle=239, enable_command_accepted=True,
                max_extended_advertising_events=255)
    add('source_closed', advertising_handle=239, status='controller_count_verified',
        controller_completed_count_verified=True, cleanup_success=True, termination_events_observed=1,
        automatic_restarts=0, automatic_fallbacks=0, termination=term,
        cleanup={k: {'status': 0, 'command_complete_received': True} for k in ('cleanup_disable', 'cleanup_remove')})
    add('source_socket_closed')
    return rows


def monitor_fixture():
    commands = [dict(hci_opcode_hex='2036', advertising_handle=239, event_properties=16, primary_channel_map=1,
                     primary_phy=1, secondary_phy=1, interval_min_ms=20, interval_max_ms=20),
                dict(hci_opcode_hex='2037', advertising_handle=239, advertising_data_length=16,
                     fragment_operation=3, owned_manufacturer_ad_exact_match=True),
                dict(hci_opcode_hex='2039', enabled=True, sets=[dict(handle=239, duration_10ms_units=0, maximum_extended_advertising_events=255)]),
                dict(hci_opcode_hex='2039', enabled=False, sets=[dict(handle=239, duration_10ms_units=0, maximum_extended_advertising_events=0)]),
                dict(hci_opcode_hex='203c', advertising_handle=239)]
    rows = []
    for i, command in enumerate(commands):
        if i == 3:
            rows.append(dict(kind='controller_advertising_set_terminated', monotonic_ns=13*SECOND, status=67,
                             advertising_handle=239, controller_reported_completed_extended_advertising_events=255))
        timestamp = (6+i if i < 3 else 13+i)*SECOND
        rows.append(dict(kind='advertising_command', monotonic_ns=timestamp, **command))
        rows.append(dict(kind='advertising_command_complete', monotonic_ns=timestamp+1000,
                         hci_opcode_hex=command['hci_opcode_hex'], status=0))
    return dict(status='completed', hci_channel=2, producer_returncode=0, producer_reaped=True,
                snaplen_truncated_packets_discarded=0, records=rows)


def receiver_fixture():
    rows = []; captures = []
    for index, seconds in enumerate((0, 8, 10, 25)):
        digest = hashlib.sha256(str(index).encode()).hexdigest()
        rows.append(dict(capture_index=index, command_start_ns=seconds*SECOND,
                         header_received_ns=seconds*SECOND+10000000, payload_received_ns=seconds*SECOND+30000000,
                         crc_and_count_valid=True, crc_ok=True, sample_count_ok=True,
                         returned_samples=16380, private_payload_sha256=digest))
        captures.append(dict(capture_index=index, payload_sha256=digest, frames=[]))
    manifest = dict(completed=True, integrity_failures=0, captures=4, nominal_rate_hz=16000000,
                    samples=16380, bits_per_component=8, frequency_mhz=2401, bandwidth_mhz=20, gain='48')
    decoded = dict(nominal_rate_hz=16000000, samples_per_capture=16380, bits_per_component=8,
                   channel=37, owned_marker_ad_hex=MARKER, frequency_translation_hz=-1000000,
                   blind_receiver_refinement=copy.deepcopy(EXPECTED_REFINEMENT), captures=captures)
    return rows, manifest, decoded


def packet(offset=1000):
    return dict(status='valid_owned', crc24_ok=True, owned_manufacturer_ad_exact_match=True,
                access_address_sample_offset=offset, access_correlation=.95, pdu_type=2, pdu_length=22,
                packet_duration_us=256, pdu_sha256='b'*64, access_address_hamming_errors=0)


class CountedReportTests(unittest.TestCase):
    def setUp(self):
        self.logs = source_fixture(); self.source = validate_source(self.logs, 255)

    def test_actual_termination_and_independent_monitor_required(self):
        self.assertEqual(self.source['controller_completed_events'], 255)
        result = validate_monitor(monitor_fixture(), self.source)
        self.assertTrue(result['matching_controller_termination'])
        self.assertIsNone(result['independently_observed_air_emission_count'])

    def test_commanded_count_summary_cannot_replace_termination(self):
        logs = [r for r in self.logs if r['kind'] != 'termination_observed']
        with self.assertRaisesRegex(ValueError, 'expected_one_termination'): validate_source(logs, 255)

    def test_extended_mode_cannot_qualify_legacy_counted_source(self):
        logs = copy.deepcopy(self.logs)
        next(r for r in logs if r['kind'] == 'configuration_requested')['event_properties'] = 0
        with self.assertRaisesRegex(ValueError, 'source_configuration_mismatch'):
            validate_source(logs, 255)
        monitor = monitor_fixture()
        next(r for r in monitor['records'] if r['kind'] == 'advertising_command')['event_properties'] = 0
        with self.assertRaisesRegex(ValueError, 'monitor_parameters_mismatch'):
            validate_monitor(monitor, self.source)

    def test_source_failures_do_not_silently_fall_back(self):
        changes = [('termination_observed', 'advertising_handle', 0), ('termination_observed', 'status', 0),
                   ('termination_observed', 'controller_reported_completed_extended_advertising_events', 100),
                   ('termination_observed', 'observed_after_enable_command_sent', False),
                   ('source_closed', 'automatic_restarts', 1), ('source_closed', 'cleanup_success', False),
                   ('configuration_requested', 'primary_channel_map', 7)]
        for kind, field, value in changes:
            with self.subTest(kind=kind, field=field):
                logs = copy.deepcopy(self.logs)
                next(r for r in logs if r['kind'] == kind)[field] = value
                with self.assertRaises(ValueError): validate_source(logs, 255)
        for kind in ('command_complete', 'command_result', 'source_socket_closed'):
            logs = copy.deepcopy(self.logs); logs.remove(next(r for r in logs if r['kind'] == kind))
            with self.assertRaises(ValueError): validate_source(logs, 255)
        duplicate = copy.deepcopy(self.logs); duplicate.insert(-2, copy.deepcopy(duplicate[-4]))
        with self.assertRaises(ValueError): validate_source(duplicate, 255)

    def test_monitor_rejects_loss_wrong_handle_and_unsuccessful_ack(self):
        for field, value in [('hci_channel', 3), ('snaplen_truncated_packets_discarded', 1), ('producer_returncode', 2)]:
            monitor = monitor_fixture(); monitor[field] = value
            with self.assertRaises(ValueError): validate_monitor(monitor, self.source)
        for kind, field, value in [('controller_advertising_set_terminated', 'advertising_handle', 1),
                                   ('advertising_command_complete', 'status', 12)]:
            monitor = monitor_fixture(); next(r for r in monitor['records'] if r['kind'] == kind)[field] = value
            with self.assertRaises(ValueError): validate_monitor(monitor, self.source)

    def test_hypothesis_duplicates_one_packet_same_payload_two_captures_two(self):
        rows, manifest, decoded = receiver_fixture()
        decoded['captures'][1]['frames'] = [packet(), packet(1002)]
        decoded['captures'][2]['frames'] = [packet()]
        result = analyze_receiver(rows, manifest, decoded, self.source)
        self.assertEqual(result['complete_crc_valid_owned_packets'], 2)
        self.assertEqual(result['not_verified_complete'], 253)
        self.assertEqual(result['capture_phases'], dict(baseline=1, source_bracket=2, post_source=1, transition=0))
        self.assertIsNone(result['unsampled_vs_truncated_vs_decoder_failure_counts'])

    def test_truncation_and_arbitrary_aa_failures_are_not_owned(self):
        rows, manifest, decoded = receiver_fixture()
        decoded['captures'][1]['frames'] = [dict(status='truncated_packet', access_address_sample_offset=1000),
                                         packet(20)]
        decoded['captures'][2]['frames'] = [{**packet(6000), 'pdu_type': 0}]
        result = analyze_receiver(rows, manifest, decoded, self.source)
        self.assertEqual(result['complete_crc_valid_owned_packets'], 0)
        self.assertEqual(result['confirmed_owned_incomplete_candidates'], 1)
        self.assertEqual(len(result['crc_valid_owned_excluded_from_count']), 2)
        self.assertEqual(result['owned_incomplete_count_bounds'], [1, 255])
        self.assertEqual(result['owned_incomplete_candidates'][0]['classification'],
                         'crc_valid_exact_owned_marker_with_clipped_nominal_packet_window')

    def test_two_owned_clusters_one_snapshot_are_not_two_source_events(self):
        rows, manifest, decoded = receiver_fixture()
        decoded['captures'][1]['frames'] = [packet(1000), packet(7000)]
        with self.assertRaisesRegex(ValueError, 'multiple_owned_clusters'):
            analyze_receiver(rows, manifest, decoded, self.source)
        # Also reject a clipped known-marker cluster plus a complete cluster.
        decoded['captures'][1]['frames'] = [packet(20), packet(7000)]
        with self.assertRaisesRegex(ValueError, 'multiple_owned_clusters'):
            analyze_receiver(rows, manifest, decoded, self.source)

    def test_exact_predeclared_search_and_period_required(self):
        for mode in ('missing', 'none', 'wider_search', 'period_missing', 'period_low', 'period_high', 'period_nan'):
            rows, manifest, decoded = receiver_fixture()
            if mode == 'missing': del decoded['blind_receiver_refinement']
            elif mode == 'none': decoded['blind_receiver_refinement'] = None
            elif mode == 'wider_search': decoded['blind_receiver_refinement']['samples_per_symbol_min'] = 3.9
            elif mode == 'period_missing': decoded['captures'][1]['frames'] = [{**packet(), 'refined': True}]
            else:
                frame = packet(); frame['samples_per_symbol_at_4msps'] = {
                    'period_low': 3.96, 'period_high': 4.04, 'period_nan': float('nan')}[mode]
                decoded['captures'][1]['frames'] = [frame]
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                analyze_receiver(rows, manifest, decoded, self.source)

    def test_all_captures_hashes_and_full_time_coverage_required(self):
        for mutation in ('missing', 'hash', 'time', 'integrity', 'duplicate_waveform'):
            rows, manifest, decoded = receiver_fixture()
            if mutation == 'missing': decoded['captures'].pop()
            elif mutation == 'hash': decoded['captures'][0]['payload_sha256'] = 'f'*64
            elif mutation == 'time': rows[-1]['payload_received_ns'] = 14*SECOND
            elif mutation == 'integrity': rows[1]['crc_and_count_valid'] = False
            else:
                rows[1]['private_payload_sha256'] = rows[0]['private_payload_sha256']
                decoded['captures'][1]['payload_sha256'] = rows[0]['private_payload_sha256']
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                analyze_receiver(rows, manifest, decoded, self.source)

    def test_three_predeclared_trials_keep_zero_hits_and_reject_missing(self):
        ids = ['counted-01', 'counted-02', 'counted-03']
        trials = []
        for trial_id, hits in zip(ids, (0, 2, 0)):
            trials.append(dict(trial_id=trial_id, source=dict(controller_completed_events=255),
                               receiver=dict(complete_crc_valid_owned_packets=hits)))
        result = aggregate(trials, ids, 255)
        self.assertEqual(result['controller_reported_completed_events'], 765)
        self.assertEqual(result['complete_crc_valid_owned_packets'], 2)
        self.assertEqual(result['not_verified_complete'], 763)
        self.assertIsNone(result['statistical_confidence_interval'])
        with self.assertRaises(ValueError): aggregate(trials[1:], ids, 255)
        with self.assertRaises(ValueError): aggregate(trials[::-1], ids, 255)

    def test_private_waveforms_recomputed_and_corruption_rejected(self):
        payload = b'\x12\x34\x56\x78'
        digest = hashlib.sha256(payload).hexdigest(); crc = f'{zlib.crc32(payload):08x}'
        rows = [dict(capture_index=0, private_payload_sha256=digest, expected_crc32=crc, actual_crc32=crc)]
        decoded = dict(samples_per_capture=2, bits_per_component=8,
                       captures=[dict(capture_filename='iq-0000.bin', payload_sha256=digest)])
        with tempfile.TemporaryDirectory() as name:
            private = Path(name); path = private/'iq-0000.bin'; path.write_bytes(payload)
            verify_private_waveforms(rows, decoded, private)
            path.write_bytes(b'\0'*4)
            with self.assertRaisesRegex(ValueError, 'hash_mismatch'): verify_private_waveforms(rows, decoded, private)
            path.write_bytes(payload); rows[0]['expected_crc32'] = '00000000'
            with self.assertRaisesRegex(ValueError, 'crc_mismatch'): verify_private_waveforms(rows, decoded, private)


if __name__ == '__main__': unittest.main()
