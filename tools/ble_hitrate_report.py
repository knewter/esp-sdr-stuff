#!/usr/bin/env python3
"""Join repeated counted-source cycles with ESP snapshots and primary decodes.

Offline only. Inputs: capture results.json/snapshots.csv (with the absolute
series_start_monotonic_ns anchor), the sanitized source JSONL, and the
ble_extended_primary decode JSON. Output: sanitized counts, expected
in-window emissions and a Poisson interval. No addresses or payloads.

Timing model: a capture's RF window lies somewhere between its host command
start and header receipt (same host CLOCK_MONOTONIC as the source container).
A capture is ON only if that whole bracket lies inside a merged source-enabled
span shrunk by the guard; OFF only if it is at least the guard away from every
span. Others are excluded as boundary captures and still reported.
"""
import argparse
import csv
import json
import math
from pathlib import Path

WINDOW_GAP_MERGE_NS = 50_000_000


def source_spans(records):
    """Return per-cycle (enable ACK, termination) spans and counted events."""
    spans, start = [], None
    counted = 0
    for record in records:
        if record.get('kind') == 'command_result' and record.get('step') == 'enable' and record.get('status') == 0:
            start = record['monotonic_ns']
        elif record.get('kind') == 'termination_observed' and start is not None:
            end = record['monotonic_ns']
            ok = (record.get('status') == 0x43 and
                  record.get('controller_reported_completed_extended_advertising_events') == 255)
            spans.append({'start_ns': start, 'end_ns': end, 'counted': ok})
            counted += 255 if ok else 0
            start = None
    return spans, counted


def merge(spans, gap_ns=WINDOW_GAP_MERGE_NS):
    merged = []
    for span in sorted(spans, key=lambda s: s['start_ns']):
        if merged and span['start_ns']-merged[-1][1] <= gap_ns:
            merged[-1][1] = max(merged[-1][1], span['end_ns'])
        else:
            merged.append([span['start_ns'], span['end_ns']])
    return merged


def classify(bracket, merged, guard_ns):
    start, end = bracket
    for low, high in merged:
        if low+guard_ns <= start and end <= high-guard_ns:
            return 'on'
    if all(end <= low-guard_ns or start >= high+guard_ns for low, high in merged):
        return 'off'
    return 'boundary'


def poisson_interval(k, z=1.96):
    """Wilson-style approximate 95% interval for a Poisson count."""
    if k == 0:
        return 0.0, 3.689  # exact one-sided 97.5% upper bound for k=0
    low = k*(1-1/(9*k)-z/(3*math.sqrt(k)))**3
    high = (k+1)*(1-1/(9*(k+1))+z/(3*math.sqrt(k+1)))**3
    return low, high


def report(results, rows, source_records, decode, guard_ms=100, window_us=None, assumed_packet_us=None):
    anchor = results['series_start_monotonic_ns']
    spans, counted = source_spans(source_records)
    if not spans:
        raise ValueError('no enabled source cycles found')
    merged = merge(spans)
    guard_ns = int(guard_ms*1e6)
    decoded = {c['capture_filename']: c for c in decode['captures']}
    classes = {'on': [], 'off': [], 'boundary': []}
    for row in rows:
        if row['status'] != 'ok':
            classes['boundary'].append(row)
            continue
        bracket = (anchor+float(row['command_start_relative_ms'])*1e6,
                   anchor+float(row['header_received_relative_ms'])*1e6)
        row['_class'] = classify(bracket, merged, guard_ns)
        classes[row['_class']].append(row)

    def frames(row, status):
        name = f"iq-{row['rate_hz']}-{row['bits_per_component']}-{int(row['attempt']):04d}.bin"
        capture = decoded.get(name)
        if capture is None:
            raise ValueError('decode missing for capture '+name)
        return [f for f in capture['frames'] if f['status'] == status]

    out = {'schema': 1, 'guard_ms': guard_ms,
           'source_cycles': len(spans), 'source_cycles_counted': sum(s['counted'] for s in spans),
           'controller_counted_events': counted,
           'source_enabled_seconds': sum(s['end_ns']-s['start_ns'] for s in spans)/1e9,
           'captures_total': len(rows),
           'captures_ok': sum(r['status'] == 'ok' for r in rows),
           'captures_on': len(classes['on']), 'captures_off': len(classes['off']),
           'captures_boundary_or_failed': len(classes['boundary'])}
    # Mean controller event spacing from counted cycles: 254 intervals per cycle.
    durations = [(s['end_ns']-s['start_ns'])/1e9 for s in spans if s['counted']]
    mean_interval_s = sum(durations)/len(durations)/254
    out['mean_event_interval_ms_from_host_brackets'] = mean_interval_s*1e3
    for name, group in (('on', classes['on']), ('off', classes['off'])):
        owned = [frames(r, 'valid_owned_primary') for r in group]
        other = [frames(r, 'valid_other_primary_redacted') for r in group]
        complete = [[f for f in fs if f['complete_preamble_and_pdu_crc_within_capture_nominal']] for fs in owned]
        out[f'{name}_owned_primary_frames'] = sum(map(len, owned))
        out[f'{name}_owned_complete_frames'] = sum(map(len, complete))
        out[f'{name}_captures_with_owned'] = sum(bool(fs) for fs in owned)
        out[f'{name}_other_valid_primary_frames'] = sum(map(len, other))
    packet_us = None
    on_frames = [f for r in classes['on'] for f in frames(r, 'valid_owned_primary')]
    if on_frames:
        packet_us = on_frames[0]['packet_duration_us']
    out['owned_packet_duration_us'] = packet_us
    if packet_us is None and assumed_packet_us is not None:
        # No owned frame decoded: use a declared nominal duration, labelled.
        packet_us = assumed_packet_us
        out['assumed_packet_duration_us'] = assumed_packet_us
    window = window_us if window_us is not None else float(rows[0]['nominal_rf_window_us'])
    out['nominal_rf_window_us'] = window
    if packet_us is not None:
        # Expected owned packets wholly inside one ON window, given mean spacing.
        per_capture = max(0.0, (window-packet_us)*1e-6)/mean_interval_s
        expected = per_capture*len(classes['on'])
        hits = out['on_owned_complete_frames']
        low, high = poisson_interval(hits)
        # Per ON window of length W, packet T, spacing I: (W+T)/I events overlap
        # it, (W-T)/I lie wholly inside and 2T/I are cut at an edge. Events with
        # no overlap with any ON window are acquisition misses.
        n_on = len(classes['on'])
        overlapping = n_on*(window+packet_us)*1e-6/mean_interval_s
        out.update(expected_overlapping_owned_events=overlapping,
                   expected_truncated_owned_events=n_on*2*packet_us*1e-6/mean_interval_s,
                   owned_truncated_frames_observed=out['on_owned_primary_frames']-out['on_owned_complete_frames'],
                   events_missed_no_window_overlap=counted-overlapping,
                   expected_complete_not_decoded=expected-hits)
        out.update(expected_complete_owned_in_on_windows=expected,
                   detection_efficiency=hits/expected if expected else None,
                   detection_efficiency_95ci=[low/expected, high/expected] if expected else None,
                   hits_per_controller_counted_event=hits/counted if counted else None)
    out['limitations'] = ('Controller-counted events, not independently observed air emissions. Host command/header '
                          'brackets bound but do not timestamp each RF window. Nominal ADC rate. Expected count '
                          'assumes uniform event phase relative to snapshots and the mean host-bracketed spacing.')
    return out


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--capture', type=Path, required=True, help='capture output dir (results.json, snapshots.csv)')
    cli.add_argument('--source', type=Path, required=True)
    cli.add_argument('--decode', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    cli.add_argument('--guard-ms', type=float, default=100)
    cli.add_argument('--assumed-packet-us', type=float,
                     help='Nominal owned packet duration when none decoded (labelled assumption)')
    args = cli.parse_args(argv)
    results = json.loads((args.capture/'results.json').read_text())
    rows = list(csv.DictReader((args.capture/'snapshots.csv').open()))
    records = [json.loads(line) for line in args.source.read_text().splitlines() if line.startswith('{')]
    out = report(results, rows, records, json.loads(args.decode.read_text()), args.guard_ms,
                 assumed_packet_us=args.assumed_packet_us)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(out, stream, indent=2)
        stream.write('\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
