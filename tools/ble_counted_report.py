#!/usr/bin/env python3
"""Offline audit of predeclared, controller-counted owned BLE receiver trials.

This tool opens no device and never stores RF payloads or device addresses.
Input source and monitor logs must already be redacted by their collectors.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import zlib

HANDLE = 239
MARKER = '0fffffff4553502d5344522d4556414c'
STEPS = [('set_parameters', '2036'), ('set_data', '2037'), ('enable', '2039'),
         ('cleanup_disable', '2039'), ('cleanup_remove', '203c')]


def require(condition, code):
    if not condition:
        raise ValueError(code)


def exactly(records, kind):
    selected = [r for r in records if r.get('kind') == kind]
    require(len(selected) == 1, 'expected_one_' + kind)
    return selected[0]


def validate_source(records, expected_count):
    require(100 <= expected_count <= 255, 'minimum_counted_emissions_gate')
    require(records and all(isinstance(r.get('monotonic_ns'), int) for r in records), 'source_timestamps_missing')
    require(all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(records, records[1:])), 'source_time_order')
    config = exactly(records, 'configuration_requested')
    fields = {'advertising_handle': HANDLE, 'event_properties': 16, 'primary_channel_map': 1,
              'primary_phy': 1, 'secondary_phy': 1, 'advertising_data_length': 16,
              'owned_manufacturer_ad_exact_match': True, 'duration_10ms_units': 0,
              'max_extended_advertising_events': expected_count}
    require(all(config.get(k) == v for k, v in fields.items()), 'source_configuration_mismatch')
    require(config.get('interval_ms') in (20, 100), 'source_interval_unsupported')
    digest = config.get('script_sha256', '')
    require(len(digest) == 64 and all(c in '0123456789abcdef' for c in digest), 'source_script_hash_missing')
    sent = [r for r in records if r.get('kind') == 'command_sent']
    require([(r.get('step'), r.get('hci_opcode_hex')) for r in sent] == STEPS, 'command_sequence_or_restart')
    results = [r for r in records if r.get('kind') == 'command_result']
    require([(r.get('step'), r.get('hci_opcode_hex')) for r in results] == STEPS, 'command_results_missing')
    require(len([r for r in records if r.get('kind') == 'command_complete']) == 5
            and not any(r.get('kind') == 'command_status' for r in records), 'unexpected_command_events')
    for request, result in zip(sent, results):
        require(request.get('advertising_handle') == HANDLE and result.get('status') == 0, 'command_not_accepted')
        require(request['monotonic_ns'] <= result['monotonic_ns'], 'command_result_before_request')
        completions = [r for r in records if r.get('kind') == 'command_complete'
                       and r.get('hci_opcode_hex') == request['hci_opcode_hex']
                       and request['monotonic_ns'] <= r['monotonic_ns'] <= result['monotonic_ns']]
        require(len(completions) == 1 and completions[0].get('status') == 0, 'successful_command_complete_missing')
    require(all(results[i]['monotonic_ns'] <= sent[i+1]['monotonic_ns'] for i in range(4)), 'command_overlap')
    enabled = exactly(records, 'source_enabled')
    require(enabled.get('advertising_handle') == HANDLE and enabled.get('enable_command_accepted') is True
            and enabled.get('max_extended_advertising_events') == expected_count, 'enable_summary_mismatch')
    term = exactly(records, 'termination_observed')
    require(term.get('advertising_handle') == HANDLE and term.get('status') == 0x43
            and term.get('controller_reported_completed_extended_advertising_events') == expected_count
            and term.get('observed_after_enable_command_sent') is True, 'termination_unverified')
    require(results[2]['monotonic_ns'] <= enabled['monotonic_ns'] <= term['monotonic_ns'] <= sent[3]['monotonic_ns'], 'termination_sequence')
    closed = exactly(records, 'source_closed')
    require(closed.get('advertising_handle') == HANDLE and closed.get('status') == 'controller_count_verified'
            and closed.get('controller_completed_count_verified') is True
            and closed.get('cleanup_success') is True and closed.get('termination_events_observed') == 1
            and closed.get('automatic_restarts') == 0 and closed.get('automatic_fallbacks') == 0, 'source_summary_unverified')
    require(all(closed.get('termination', {}).get(k) == term.get(k) for k in
                ('status', 'advertising_handle', 'controller_reported_completed_extended_advertising_events', 'observed_after_enable_command_sent')), 'termination_summary_mismatch')
    require(all(closed.get('cleanup', {}).get(step, {}).get('status') == 0
                and closed['cleanup'][step].get('command_complete_received') is True
                for step in ('cleanup_disable', 'cleanup_remove')), 'cleanup_unverified')
    socket_closed = exactly(records, 'source_socket_closed')
    require(results[-1]['monotonic_ns'] <= closed['monotonic_ns'] <= socket_closed['monotonic_ns'], 'cleanup_not_closed')
    return {'controller_completed_events': expected_count, 'enable_command_sent_ns': sent[2]['monotonic_ns'],
            'termination_observed_ns': term['monotonic_ns'], 'source_closed_ns': socket_closed['monotonic_ns'],
            'source_script_sha256': digest, 'interval_ms': config['interval_ms']}


def validate_monitor(monitor, source):
    require(monitor.get('status') == 'completed' and monitor.get('hci_channel') == 2
            and monitor.get('producer_returncode') == 0 and monitor.get('producer_reaped') is True
            and monitor.get('snaplen_truncated_packets_discarded') == 0, 'monitor_incomplete')
    rows = monitor['records']
    commands = [r for r in rows if r.get('kind') == 'advertising_command']
    # A different handle or an unexpected reconfiguration is not silently ignored.
    require([r.get('hci_opcode_hex') for r in commands] == ['2036', '2037', '2039', '2039', '203c'], 'monitor_command_sequence')
    params, data, enable, disable, remove = commands
    require(remove.get('advertising_handle') == HANDLE, 'monitor_remove_handle_mismatch')
    require(params.get('advertising_handle') == HANDLE and params.get('event_properties') == 16
            and params.get('primary_channel_map') == 1 and params.get('primary_phy') == 1
            and params.get('secondary_phy') == 1
            and params.get('interval_min_ms') == source['interval_ms']
            and params.get('interval_max_ms') == source['interval_ms'], 'monitor_parameters_mismatch')
    require(data.get('advertising_handle') == HANDLE and data.get('advertising_data_length') == 16
            and data.get('fragment_operation') == 3 and data.get('owned_manufacturer_ad_exact_match') is True, 'monitor_data_mismatch')
    for command, on in ((enable, True), (disable, False)):
        require(command.get('enabled') is on and command.get('sets') == [{'handle': HANDLE, 'duration_10ms_units': 0,
                'maximum_extended_advertising_events': source['controller_completed_events'] if on else 0}], 'monitor_enable_mismatch')
    term = exactly(rows, 'controller_advertising_set_terminated')
    require(term.get('status') == 0x43 and term.get('advertising_handle') == HANDLE
            and term.get('controller_reported_completed_extended_advertising_events') == source['controller_completed_events'], 'monitor_termination_mismatch')
    require(enable['monotonic_ns'] <= term['monotonic_ns'] <= disable['monotonic_ns'], 'monitor_termination_sequence')
    # Sequential commands can share an opcode (enable/disable); match in order.
    pending = None
    accepted = []
    for row in rows:
        if row.get('kind') == 'advertising_command':
            require(pending is None, 'monitor_command_overlap')
            pending = row['hci_opcode_hex']
        elif row.get('kind') == 'advertising_command_complete':
            require(pending == row.get('hci_opcode_hex') and row.get('status') == 0, 'monitor_completion_mismatch')
            accepted.append(pending)
            pending = None
    require(pending is None and accepted == ['2036', '2037', '2039', '2039', '203c'], 'monitor_completions_missing')
    return {'matching_controller_termination': True, 'loss_free_monitor_proven': False,
            'independently_observed_air_emission_count': None}


def true(value):
    return value is True or value == 'True'


def analyze_receiver(rows, manifest, decoded, source):
    require(manifest.get('completed') is True and manifest.get('integrity_failures') == 0, 'receiver_not_complete')
    require(len(rows) == manifest.get('captures') == len(decoded.get('captures', [])), 'all_capture_coverage_missing')
    require(rows and [int(r['capture_index']) for r in rows] == list(range(len(rows))), 'capture_index_sequence')
    require([c['capture_index'] for c in decoded['captures']] == list(range(len(rows))), 'decoder_index_sequence')
    rate = decoded['nominal_rate_hz']; samples = decoded['samples_per_capture']
    require(rate == 16000000 and samples == 16380 and decoded.get('bits_per_component') == 8
            and manifest.get('frequency_mhz') == 2401 and manifest.get('bandwidth_mhz') == 20
            and str(manifest.get('gain')) == '48', 'predeclared_receiver_settings_mismatch')
    require(rate == manifest.get('nominal_rate_hz') and samples == manifest.get('samples')
            and decoded.get('bits_per_component') == manifest.get('bits_per_component')
            and decoded.get('channel') == 37 and decoded.get('owned_marker_ad_hex') == MARKER, 'decoder_configuration_mismatch')
    require(decoded.get('frequency_translation_hz') == (manifest['frequency_mhz'] - 2402)*1000000, 'decoder_frequency_translation_mismatch')
    enable = source['enable_command_sent_ns']; term = source['termination_observed_ns']; closed = source['source_closed_ns']
    first = int(rows[0]['command_start_ns']); last = int(rows[-1]['payload_received_ns'])
    require(enable - first >= 5000000000 and last - closed >= 10000000000, 'baseline_or_post_source_coverage_short')
    counts = {'baseline': 0, 'source_bracket': 0, 'post_source': 0, 'transition': 0}
    packets = []; excluded = []; incomplete = []; previous_end = None; hashes = set(); sampled_us = 0
    for row, capture in zip(rows, decoded['captures']):
        start, header, end = (int(row[k]) for k in ('command_start_ns', 'header_received_ns', 'payload_received_ns'))
        require(start <= header <= end and (previous_end is None or start >= previous_end), 'receiver_time_overlap')
        previous_end = end
        require(true(row['crc_and_count_valid']) and true(row['crc_ok']) and true(row['sample_count_ok'])
                and int(row['returned_samples']) == samples, 'receiver_transport_integrity_failed')
        require(row['private_payload_sha256'] == capture['payload_sha256'], 'decoder_capture_hash_mismatch')
        require(capture['payload_sha256'] not in hashes, 'repeated_waveform_identity_unresolved')
        hashes.add(capture['payload_sha256'])
        phase = 'baseline' if header < enable else ('source_bracket' if start >= enable and header <= term
                else ('post_source' if start >= closed else 'transition'))
        counts[phase] += 1
        if phase == 'source_bracket': sampled_us += samples / rate * 1000000
        accepted = []
        for frame in sorted(capture['frames'], key=lambda f: -f.get('access_correlation', 0)):
            if frame.get('status') != 'valid_owned': continue
            require(frame.get('crc24_ok') is True and frame.get('owned_manufacturer_ad_exact_match') is True, 'owned_decode_proof_missing')
            require(isinstance(frame.get('pdu_sha256'), str) and len(frame['pdu_sha256']) == 64, 'owned_pdu_hash_missing')
            offset = frame['access_address_sample_offset']
            if any(abs(offset - old['access_address_sample_offset']) <= rate / 1000000 * 4 for old in accepted): continue
            accepted.append(frame)
            period = frame.get('samples_per_symbol_at_4msps', 4)
            begin = frame.get('nominal_packet_start_sample', (offset / (rate/4000000)-8*period)*(rate/4000000))
            finish = frame.get('nominal_packet_end_sample', begin + frame['packet_duration_us']*period*(rate/4000000))
            reason = None
            if phase != 'source_bracket': reason = 'outside_unambiguous_source_host_bracket'
            elif frame.get('pdu_type') != 2 or frame.get('pdu_length') != 22 or frame.get('packet_duration_us') != 256:
                reason = 'source_pdu_configuration_mismatch'
            elif not all(math.isfinite(v) for v in (begin, finish, offset, period)) or not 0 <= begin < finish <= samples:
                reason = 'complete_packet_window_unverified'
            elif frame.get('complete_preamble_and_pdu_crc_within_capture_nominal') is False: reason = 'complete_packet_window_unverified'
            record = {'capture_index': capture['capture_index'], 'waveform_sha256': capture['payload_sha256'],
                      'pdu_sha256': frame.get('pdu_sha256'), 'access_address_sample_offset': offset,
                      'nominal_packet_start_sample': begin, 'nominal_packet_end_sample': finish,
                      'pdu_type': frame.get('pdu_type'), 'pdu_length': frame.get('pdu_length'),
                      'preamble_hamming_errors': frame.get('preamble_hamming_errors'),
                      'access_address_hamming_errors': frame.get('access_address_hamming_errors')}
            if reason:
                excluded.append({**record, 'exclusion_reason': reason})
                # A complete CRC-protected exact marker independently supports
                # ownership even when the nominal preamble window is clipped.
                # Failed/truncated AA-only candidates never reach this branch.
                if reason == 'complete_packet_window_unverified' and phase == 'source_bracket' and (
                        math.isfinite(begin) and math.isfinite(finish) and (begin < 0 or finish > samples)):
                    incomplete.append({**record, 'classification': 'crc_valid_exact_owned_marker_with_clipped_nominal_packet_window'})
            else: packets.append(record)
    n = source['controller_completed_events']; hits = len(packets)
    require(hits + len(incomplete) <= n, 'numerator_exceeds_controller_events')
    return {'captures_replayed': len(rows), 'capture_phases': counts, 'complete_crc_valid_owned_packets': hits,
            'owned_packets': packets, 'crc_valid_owned_excluded_from_count': excluded,
            'not_verified_complete': n - hits, 'complete_recovery_fraction': hits/n,
            'any_owned_observation_fraction_bounds': [(hits+len(incomplete))/n, 1.0],
            'confirmed_owned_incomplete_candidates': len(incomplete),
            'owned_incomplete_candidates': incomplete,
            'owned_incomplete_count_bounds': [len(incomplete), n-hits],
            'unsampled_vs_truncated_vs_decoder_failure_counts': None,
            'source_bracket_nominal_sampled_microseconds': sampled_us,
            'source_bracket_host_elapsed_seconds': (term-enable)/1000000000,
            'host_acquisition_brackets_are_rf_timestamps': False,
            'baseline_before_enable_seconds': (enable-first)/1000000000,
            'post_cleanup_seconds': (last-closed)/1000000000}


def aggregate(trials, expected_ids, expected_count):
    require(len(set(expected_ids)) == len(expected_ids) and len(expected_ids) == 3, 'predeclared_three_trial_ids_required')
    require([t['trial_id'] for t in trials] == expected_ids, 'missing_duplicate_or_reordered_trial')
    require(all(t['source']['controller_completed_events'] == expected_count for t in trials), 'trial_count_mismatch')
    n = expected_count*len(trials); hits = sum(t['receiver']['complete_crc_valid_owned_packets'] for t in trials)
    incomplete = sum(t['receiver'].get('confirmed_owned_incomplete_candidates', 0) for t in trials)
    return {'schema': 1, 'predeclared_trial_ids': expected_ids, 'trials': trials,
            'controller_reported_completed_events': n, 'complete_crc_valid_owned_packets': hits,
            'complete_recovery_fraction': hits/n, 'not_verified_complete': n-hits,
            'any_owned_observation_fraction_bounds': [(hits+incomplete)/n, 1.0],
            'confirmed_owned_incomplete_candidates': incomplete,
            'owned_incomplete_count_bounds': [incomplete, n-hits],
            'count_unit': 'Controller-reported completed advertising events; one legacy nonconnectable LE1M primary-channel-37 packet per event under verified configuration.',
            'independently_observed_air_emission_count': None,
            'statistical_confidence_interval': None,
            'limitations': 'Descriptive recovery fraction for these predeclared trials, not an IID population estimate. Host timestamps bracket acquisition; no hardware RF timestamp or calibrated sample clock. N minus full verified hits is not verified complete: unsampled events, truncation, receiver/decoder failures and source-path uncertainty are unresolved. No arbitrary AA candidate is attributed to the owned source; incomplete-observation bounds concern the remaining unverified events and are conservative. Controller count is not an independent RF counter.'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_private_waveforms(rows, decoded, private):
    """Independently recompute transport CRC, length and hashes for every input."""
    require(len(rows) == len(decoded['captures']), 'all_capture_coverage_missing')
    expected_size = (decoded['samples_per_capture']*decoded['bits_per_component']*2+7)//8
    for row, capture in zip(rows, decoded['captures']):
        filename = capture.get('capture_filename', '')
        require(filename == f'iq-{int(row["capture_index"]):04d}.bin', 'private_capture_filename_mismatch')
        payload = (private/filename).read_bytes()
        require(len(payload) == expected_size, 'private_waveform_size_mismatch')
        require(hashlib.sha256(payload).hexdigest() == capture['payload_sha256'] == row['private_payload_sha256'], 'private_waveform_hash_mismatch')
        require(f'{zlib.crc32(payload):08x}' == row['actual_crc32'] == row['expected_crc32'], 'private_waveform_transport_crc_mismatch')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--plan', type=Path, required=True, help='JSON with expected_ids, expected_count and trials (trial_id, source, monitor, captures, receiver, decoder, private paths)')
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    require(not args.output.exists(), 'fresh_output_required')
    plan = json.loads(args.plan.read_text()); trials = []; source_hashes = set(); capture_hashes = set()
    for item in plan['trials']:
        paths = {k: args.plan.parent / item[k] for k in ('source', 'monitor', 'captures', 'receiver', 'decoder')}
        records = [json.loads(line) for line in paths['source'].read_text().splitlines() if line.strip()]
        source = validate_source(records, plan['expected_count'])
        monitor = validate_monitor(json.loads(paths['monitor'].read_text()), source)
        with paths['captures'].open() as stream: rows = list(csv.DictReader(stream))
        decoded = json.loads(paths['decoder'].read_text())
        verify_private_waveforms(rows, decoded, args.plan.parent/item['private'])
        receiver = analyze_receiver(rows, json.loads(paths['receiver'].read_text()), decoded, source)
        require(digest(paths['source']) not in source_hashes and digest(paths['captures']) not in capture_hashes, 'reused_trial_evidence')
        source_hashes.add(digest(paths['source'])); capture_hashes.add(digest(paths['captures']))
        trials.append({'trial_id': item['trial_id'], 'source': source, 'monitor': monitor, 'receiver': receiver,
                       'input_sha256': {k: digest(p) for k, p in paths.items()}})
    report = aggregate(trials, plan['expected_ids'], plan['expected_count'])
    report['predeclared_plan_sha256'] = digest(args.plan)
    report['reporter_script_sha256'] = digest(Path(__file__))
    report['decoder_script_sha256'] = digest(Path(__file__).with_name('ble_decode_iq.py'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as sink: sink.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('controller_reported_completed_events', 'complete_crc_valid_owned_packets', 'not_verified_complete')}))


if __name__ == '__main__': main()
