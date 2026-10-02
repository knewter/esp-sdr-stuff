#!/usr/bin/env python3
"""Blind offline RF discriminator; zero HCI count never becomes a RF denominator."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from ble_counted_report import EXPECTED_REFINEMENT, STEPS, exactly, require, true, verify_private_waveforms

DECODER_SHA256 = '834fdd78e3221d0625eaa7cf1059b9bd59d3b8b9fa929578f2555bff64130128'
GUARD_NS = 100000000
IDS = [f'zero-counter-{i:02d}' for i in range(1, 11)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_episode(records, monitor, summary):
    """Verify a failed counted-source diagnostic without relabelling it success."""
    require(all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(records, records[1:])), 'source_time_order')
    config = exactly(records, 'configuration_requested')
    expected = dict(advertising_handle=1, event_properties=16, primary_channel_map=1, primary_phy=1,
                    secondary_phy=1, interval_ms=20, advertising_data_length=16,
                    owned_manufacturer_ad_exact_match=True, max_extended_advertising_events=255,
                    duration_10ms_units=500, duration_diagnostic_requested=True, handle_diagnostic_requested=True)
    require(all(config.get(k) == v for k, v in expected.items()), 'source_configuration_mismatch')
    require(exactly(records, 'source_ready').get('start_delay_s') == 0, 'source_start_delay_not_zero')
    sent = [r for r in records if r.get('kind') == 'command_sent']
    results = [r for r in records if r.get('kind') == 'command_result']
    complete = [r for r in records if r.get('kind') == 'command_complete']
    require([(r.get('step'), r.get('hci_opcode_hex')) for r in sent] == STEPS
            and [(r.get('step'), r.get('hci_opcode_hex')) for r in results] == STEPS
            and len(complete) == 5, 'source_command_sequence')
    for i, (request, result, ack) in enumerate(zip(sent, results, complete)):
        require(request.get('advertising_handle') == 1 and result.get('status') == ack.get('status') == 0
                and ack.get('hci_opcode_hex') == request['hci_opcode_hex']
                and request['monotonic_ns'] <= ack['monotonic_ns'] <= result['monotonic_ns'], 'source_ack_mismatch')
        if i < 4: require(result['monotonic_ns'] <= sent[i+1]['monotonic_ns'], 'source_command_overlap')
    enabled = exactly(records, 'source_enabled')
    require(enabled.get('enable_command_accepted') is True and enabled.get('advertising_handle') == 1
            and enabled.get('max_extended_advertising_events') == 255, 'source_enable_mismatch')
    term = exactly(records, 'termination_observed')
    termfields = dict(status=60, advertising_handle=1, controller_reported_completed_extended_advertising_events=0)
    require(all(term.get(k) == v for k, v in termfields.items())
            and term.get('observed_after_enable_command_sent') is True, 'source_zero_counter_receipt_mismatch')
    require(results[2]['monotonic_ns'] <= enabled['monotonic_ns'] <= term['monotonic_ns'] <= sent[3]['monotonic_ns'], 'source_termination_sequence')
    closed = exactly(records, 'source_closed')
    require(closed == summary and closed.get('status') == 'trial_failed'
            and closed.get('error_code') == 'termination_status_or_count_mismatch'
            and closed.get('controller_completed_count_verified') is False
            and closed.get('automatic_restarts') == closed.get('automatic_fallbacks') == 0
            and closed.get('termination_events_observed') == 1 and closed.get('cleanup_success') is True,
            'diagnostic_failure_not_preserved')
    require(all(closed.get('termination', {}).get(k) == v for k, v in termfields.items()), 'summary_termination_mismatch')
    require(all(closed['cleanup'][step].get('status') == 0
                and closed['cleanup'][step].get('command_complete_received') is True
                for step in ('cleanup_disable', 'cleanup_remove')), 'source_cleanup_mismatch')
    socket_closed = exactly(records, 'source_socket_closed')
    require(results[-1]['monotonic_ns'] <= closed['monotonic_ns'] <= socket_closed['monotonic_ns'], 'source_socket_not_closed')
    require(len(monitor) == 11, 'monitor_episode_incomplete')
    require([r['kind'] for r in monitor] == ['advertising_command', 'advertising_command_complete']*3
            + ['controller_advertising_set_terminated'] + ['advertising_command', 'advertising_command_complete']*2,
            'monitor_episode_order')
    cmds = [monitor[i] for i in (0, 2, 4, 7, 9)]
    acks = [monitor[i] for i in (1, 3, 5, 8, 10)]
    require([r.get('hci_opcode_hex') for r in cmds] == [opcode for _, opcode in STEPS], 'monitor_command_sequence')
    require(all(a.get('hci_opcode_hex') == c.get('hci_opcode_hex') and a.get('status') == 0 for c, a in zip(cmds, acks)), 'monitor_ack_mismatch')
    params, data, enable, disable, remove = cmds
    require(all(params.get(k) == v for k, v in dict(advertising_handle=1, event_properties=16,
                primary_channel_map=1, primary_phy=1, secondary_phy=1, interval_min_ms=20, interval_max_ms=20).items()), 'monitor_parameters_mismatch')
    require(data.get('advertising_handle') == 1 and data.get('fragment_operation') == 3
            and data.get('advertising_data_length') == 16 and data.get('owned_manufacturer_ad_exact_match') is True, 'monitor_marker_mismatch')
    for command, on in ((enable, True), (disable, False)):
        require(command.get('enabled') is on and command.get('sets') == [dict(handle=1,
                duration_10ms_units=500 if on else 0, maximum_extended_advertising_events=255 if on else 0)], 'monitor_enable_mismatch')
    require(remove.get('advertising_handle') == 1, 'monitor_cleanup_handle_mismatch')
    observed = monitor[6]
    require(all(observed.get(k) == v for k, v in termfields.items()), 'monitor_zero_counter_receipt_mismatch')
    require(all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(monitor, monitor[1:])), 'monitor_time_order')
    require(abs(observed['monotonic_ns']-term['monotonic_ns']) < GUARD_NS
            and abs(acks[2]['monotonic_ns']-results[2]['monotonic_ns']) < GUARD_NS, 'independent_receipts_clock_alignment')
    return dict(enable_sent_ns=sent[2]['monotonic_ns'], enable_accepted_ns=results[2]['monotonic_ns'],
                termination_observed_ns=term['monotonic_ns'], source_closed_ns=socket_closed['monotonic_ns'],
                guarded_start_ns=max(results[2]['monotonic_ns'], acks[2]['monotonic_ns'])+GUARD_NS,
                guarded_end_ns=min(term['monotonic_ns'], observed['monotonic_ns'])-GUARD_NS,
                controller_reported_completed_events=0, actual_rf_emissions=None,
                source_returncode=2, original_source_status=closed['status'],
                native_and_monitor_zero_counter_match=True, cleanup_acknowledgements_all_zero=True,
                source_script_sha256=config['script_sha256'])


def phase(start, end, episodes):
    for episode in episodes:
        if start >= episode['guarded_start_ns'] and end <= episode['guarded_end_ns']:
            return episode['episode_id']
    if end < episodes[0]['enable_sent_ns']-GUARD_NS: return 'source_off_before'
    for previous, following in zip(episodes, episodes[1:]):
        if start > previous['source_closed_ns']+GUARD_NS and end < following['enable_sent_ns']-GUARD_NS:
            return 'source_off_gap_after_'+previous['episode_id']
    if start > episodes[-1]['source_closed_ns']+GUARD_NS: return 'source_off_after'
    return 'control_boundary_excluded'


def coverage(main_rows, tail_rows, episodes):
    first = int(main_rows[0]['command_start_ns']); last = int(main_rows[-1]['payload_received_ns'])
    closed = episodes[-1]['source_closed_ns']
    gap = (int(tail_rows[0]['command_start_ns'])-last)/1e9
    require(gap > 0, 'extension_is_not_separate')
    return dict(baseline_before_first_enable_seconds=(episodes[0]['enable_sent_ns']-first)/1e9,
                original_post_cleanup_tail_seconds=(last-closed)/1e9,
                original_tail_more_than_ten_seconds=(last-closed) > 10000000000,
                supplemental_segment_gap_seconds=gap,
                supplemental_segment_elapsed_seconds=(int(tail_rows[-1]['payload_received_ns'])-int(tail_rows[0]['command_start_ns']))/1e9,
                supplemental_segment_starts_after_cleanup_seconds=(int(tail_rows[0]['command_start_ns'])-closed)/1e9,
                continuous_tail_requirement_repaired_by_extension=False,
                original_schedule_acceptance=False if last-closed <= 10000000000 else True)


def analyze_segment(rows, decoded, episodes, segment):
    require(len(rows) == len(decoded['captures']) and [int(r['capture_index']) for r in rows] == list(range(len(rows)))
            and [c['capture_index'] for c in decoded['captures']] == list(range(len(rows))), 'capture_coverage_missing')
    require(decoded.get('blind_receiver_refinement') == EXPECTED_REFINEMENT, 'blind_search_changed')
    phases = {}; hits = []; excluded = []; previous_end = None
    for row, capture in zip(rows, decoded['captures']):
        start, header, end = (int(row[k]) for k in ('command_start_ns', 'header_received_ns', 'payload_received_ns'))
        require(start <= header <= end and (previous_end is None or start >= previous_end), 'receiver_time_order')
        previous_end = end
        require(all(true(row[k]) for k in ('crc_and_count_valid', 'crc_ok', 'sample_count_ok'))
                and int(row['returned_samples']) == 16380, 'capture_integrity_failed')
        label = phase(start, end, episodes)
        capture.update(segment=segment, source_control_phase=label, command_start_ns=start,
                       header_received_ns=header, payload_received_ns=end)
        counts = phases.setdefault(label, dict(captures=0, captures_with_aa_candidates=0, exact_owned_complete_packets=0))
        counts['captures'] += 1; counts['captures_with_aa_candidates'] += bool(capture['frames'])
        clusters = []
        for frame in sorted(capture['frames'], key=lambda f: -f.get('access_correlation', 0)):
            if frame.get('status') != 'valid_owned': continue
            require(frame.get('crc24_ok') is True and frame.get('owned_manufacturer_ad_exact_match') is True, 'owned_marker_crc_missing')
            offset = frame['access_address_sample_offset']
            if any(abs(offset-other['access_address_sample_offset']) <= 64 for other in clusters): continue
            clusters.append(frame)
            period = frame.get('samples_per_symbol_at_4msps', 4)
            require(3.97 <= period <= 4.03, 'receiver_period_changed')
            beginning = frame.get('nominal_packet_start_sample', offset-8*period*4)
            ending = frame.get('nominal_packet_end_sample', beginning+frame['packet_duration_us']*period*4)
            record = dict(segment=segment, capture_index=capture['capture_index'], source_control_phase=label,
                          waveform_sha256=capture['payload_sha256'], pdu_sha256=frame.get('pdu_sha256'),
                          nominal_packet_start_sample=beginning, nominal_packet_end_sample=ending,
                          access_address_hamming_errors=frame.get('access_address_hamming_errors'),
                          preamble_hamming_errors=frame.get('preamble_hamming_errors'))
            reasons = []
            if label not in IDS: reasons.append('outside_guarded_episode')
            if frame.get('pdu_type') != 2 or frame.get('pdu_length') != 22 or frame.get('packet_duration_us') != 256:
                reasons.append('source_pdu_mismatch')
            if not 0 <= beginning < ending <= 16380 or frame.get('complete_preamble_and_pdu_crc_within_capture_nominal') is False:
                reasons.append('complete_packet_window_unverified')
            if reasons: excluded.append({**record, 'exclusion_reasons': reasons})
            else: hits.append(record); counts['exact_owned_complete_packets'] += 1
        require(len(clusters) <= 1 or label not in IDS, 'multiple_owned_clusters_in_one_snapshot_unresolved')
    return dict(segment=segment, captures=len(rows), phases=phases, complete_owned_packets=hits,
                excluded_crc_valid_owned_candidates=excluded,
                first_command_start_ns=int(rows[0]['command_start_ns']), last_payload_received_ns=int(rows[-1]['payload_received_ns']))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--input', type=Path, required=True, help='Private root dataset directory')
    cli.add_argument('--output', type=Path, required=True, help='Fresh public analysis filenames; root receipts may already exist')
    args = cli.parse_args(); base = args.input; out = args.output
    out.mkdir(parents=True, exist_ok=True)
    for name in ('analysis.json', 'decoder-main.json', 'decoder-tail.json'):
        require(not (out/name).exists(), 'fresh_analysis_output_required')
    decoder = Path(__file__).with_name('ble_decode_iq.py')
    require(sha(decoder) == DECODER_SHA256, 'pinned_decoder_source_changed')
    monitor = json.loads((base/'hci-control.json').read_text())
    require(monitor.get('status') == 'completed' and monitor.get('hci_channel') == 2
            and monitor.get('producer_returncode') == 0 and monitor.get('producer_reaped') is True
            and monitor.get('snaplen_truncated_packets_discarded') == 0 and len(monitor['records']) == 110,
            'complete_monitor_interval_missing')
    source_entries = json.loads((base/'source-episodes.json').read_text())
    require([e['episode_id'] for e in source_entries] == IDS, 'all_ten_episodes_missing')
    episodes = []; receipts = dict(monitor=sha(base/'hci-control.json'), source_episodes=sha(base/'source-episodes.json'))
    for i, entry in enumerate(source_entries):
        path = base/'sources'/entry['episode_id']/'source-control.jsonl'
        require(entry['source_returncode'] == 2, 'diagnostic_returncode_changed')
        records = [json.loads(line) for line in path.read_text().splitlines()]
        episode = check_episode(records, monitor['records'][i*11:(i+1)*11], entry['summary'])
        episode['episode_id'] = entry['episode_id']; episodes.append(episode)
        receipts[entry['episode_id']] = sha(path)
    segments = []; all_rows = []; all_hashes = set()
    for name, receiver, private in [('main', 'receiver', 'iq'), ('tail', 'receiver-tail', 'iq-tail')]:
        physical = json.loads((base/receiver/'manifest.json').read_text())
        require(physical.get('completed') is True and physical.get('integrity_failures') == 0, 'receiver_not_complete')
        require(all(physical.get(k) == v for k, v in dict(nominal_rate_hz=16000000, bits_per_component=8,
                    samples=16380, frequency_mhz=2401, bandwidth_mhz=20, gain='48').items()), 'receiver_settings_changed')
        with (base/receiver/'captures.csv').open() as stream: rows = list(csv.DictReader(stream))
        require(len(rows) == physical['captures'] == len(list((base/private).glob('*.bin'))), 'waveform_coverage_missing')
        target = out/f'decoder-{name}.json'
        subprocess.run([sys.executable, str(decoder), '--input', str(base/private), '--output', str(target),
                        '--rate', '16000000', '--bits', '8', '--samples', '16380', '--channel', '37',
                        '--frequency-translation-hz', '-1000000', '--refine'], check=True)
        decoded = json.loads(target.read_text()); verify_private_waveforms(rows, decoded, base/private)
        for capture in decoded['captures']:
            require(capture['payload_sha256'] not in all_hashes, 'repeated_waveform_provenance_unresolved')
            all_hashes.add(capture['payload_sha256'])
        decoded['decoder_script_sha256'] = sha(decoder)
        decoded['decoder_origin_commit'] = 'a73148e90c76ead4236e8881f813e7758b19f833'
        decoded['replay_repository_revision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=decoder.parent.parent, text=True).strip()
        decoded['physical_capture_csv_sha256'] = sha(base/receiver/'captures.csv')
        decoded['source_control_guard_ms'] = 100
        segments.append(analyze_segment(rows, decoded, episodes, name)); all_rows.append(rows)
        target.write_text(json.dumps(decoded, indent=2)+'\n')
        receipts[receiver+'_manifest'] = sha(base/receiver/'manifest.json')
        receipts[receiver+'_csv'] = sha(base/receiver/'captures.csv')
    schedule = coverage(all_rows[0], all_rows[1], episodes)
    owned = [packet for segment in segments for packet in segment['complete_owned_packets']]
    report = dict(schema=1, experiment='predeclared zero-controller-counter RF discriminator',
                  decoder_script_sha256=sha(decoder), reporter_script_sha256=sha(Path(__file__)),
                  input_receipt_sha256=receipts, source_control_guard_ms=100, episodes=episodes,
                  segments=segments, captures_replayed=sum(s['captures'] for s in segments),
                  raw_waveforms_all_hash_crc_count_verified=True, schedule=schedule,
                  complete_crc_valid_exact_owned_packets=len(owned), actual_rf_event_count=None,
                  reception_rate=None, counted_event_gate_accepted=False,
                  zero_count_proves_no_emission=False,
                  outcome='positive_owned_reception_despite_zero_counter' if owned else 'inconclusive_no_verified_owned_packet',
                  limitations='Zero controller count is not an RF emission count. Null replay cannot distinguish no emission from sparse sampling or receiver/decoder limitations. Original short tail and supplemental segment/gap remain separate; extension does not repair continuous schedule compliance. Host control timestamps and nominal sample bounds are not hardware RF timestamps. No arbitrary AA candidate is attributed to the source. No population rate or >=100 counted-event acceptance.')
    (out/'analysis.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(captures=report['captures_replayed'], owned=report['complete_crc_valid_exact_owned_packets'],
                          outcome=report['outcome'], schedule=schedule), indent=2))


if __name__ == '__main__': main()
