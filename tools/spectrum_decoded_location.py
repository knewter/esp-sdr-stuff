#!/usr/bin/env python3
"""Offline channel location from decoded owned packets (spectrum session 002, part A).

Inputs per channel: the capture folder (results.json, snapshots.csv), the
source JSONL, and one ble_extended_primary decode JSON per grid translation.
A packet is counted once: the same window and access-address position within
4 us is one packet across grid points. Its absolute carrier is
LO - translation + the decoder's residual estimate. No hardware access.
"""
import argparse
import csv
import json
from pathlib import Path
import statistics

from ble_hitrate_report import merge, source_spans

RATE = 16_000_000
DEDUP_SAMPLES = 4*RATE//1_000_000


def owned_packets(decode_paths):
    """Deduplicated owned packets: {window: [(sample_offset, abs_carrier_hz)]}."""
    found = {}
    for path, translation in decode_paths:
        d = json.loads(Path(path).read_text())
        lo_hz = d.get('lo_hz')
        for capture in d['captures']:
            for f in capture['frames']:
                if f.get('status') != 'valid_owned_primary':
                    continue
                offset = f['access_address_sample_offset']
                bucket = found.setdefault(capture['capture_filename'], [])
                if any(abs(offset-o) < DEDUP_SAMPLES for o, _, _ in bucket):
                    continue
                bucket.append((offset, translation, f.get('estimated_carrier_offset_hz')))
    return found


def locate(capture, source_jsonl, decode_paths, lo_mhz, nominal_mhz, guard_ms=100):
    capture = Path(capture)
    results = json.loads((capture/'results.json').read_text())
    anchor = results['series_start_monotonic_ns']
    rows = [r for r in csv.DictReader((capture/'snapshots.csv').open()) if r['status'] == 'ok']
    records = [json.loads(l) for l in Path(source_jsonl).read_text().splitlines() if l.startswith('{')]
    spans, counted = source_spans(records)
    merged = merge(spans)
    packets = owned_packets(decode_paths)
    guard = int(guard_ms*1e6)
    name = lambda r: f"iq-{r['rate_hz']}-{r['bits_per_component']}-{int(r['attempt']):04d}.bin"
    carrier = lambda t, res: (lo_mhz*1e6-t+(res or 0.0))/1e6
    pairs, all_on, off_total = [], [], 0
    for i, (low, high) in enumerate(merged):
        prev = merged[i-1][1] if i else anchor
        on_c, off_n = [], 0
        for r in rows:
            start = anchor+float(r['command_start_relative_ms'])*1e6
            end = anchor+float(r['header_received_relative_ms'])*1e6
            hits = packets.get(name(r), [])
            if low+guard <= start and end <= high-guard:
                on_c += [carrier(t, res) for _, t, res in hits]
            elif prev+guard <= start and end <= low-guard:
                off_n += len(hits)
        off_total += off_n
        all_on += on_c
        pairs.append({'pair': i+1, 'owned_on': len(on_c), 'owned_off': off_n,
                      'median_carrier_mhz': statistics.median(on_c) if on_c else None,
                      'offset_from_nominal_khz': (statistics.median(on_c)-nominal_mhz)*1e3 if on_c else None})
    tail = [r for r in rows if anchor+float(r['command_start_relative_ms'])*1e6 >= merged[-1][1]+guard] if merged else []
    off_total += sum(len(packets.get(name(r), [])) for r in tail)
    return {'nominal_mhz': nominal_mhz, 'lo_mhz': lo_mhz, 'source_cycles': len(spans), 'controller_counted_events': counted,
            'pairs': pairs, 'owned_off_total': off_total,
            'median_carrier_mhz': statistics.median(all_on) if all_on else None,
            'offset_from_nominal_khz': (statistics.median(all_on)-nominal_mhz)*1e3 if all_on else None,
            'carrier_spread_khz': [(min(all_on)-nominal_mhz)*1e3, (max(all_on)-nominal_mhz)*1e3] if all_on else None,
            'confirmed': len(pairs) >= 3 and all(p['owned_on'] >= 1 for p in pairs) and off_total == 0}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--session', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    cli.add_argument('--grid-khz', type=int, nargs='+', default=[-600, -1000, -1400, -1800, -2200, -2600, -3000])
    a = cli.parse_args()
    out = {}
    for ch, nominal in ((37, 2402), (38, 2426), (39, 2480)):
        cap = a.session/f'a-ch{ch}'
        if not (cap/'results.json').exists():
            continue
        decodes = [(a.session/f'a-ch{ch}-decode{k}.json', k*1000) for k in a.grid_khz]
        decodes = [(p, t) for p, t in decodes if p.exists()]
        out[f'ch{ch}'] = locate(cap, a.session/f'a-ch{ch}-source.jsonl', decodes, nominal-1, nominal)
    a.output.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
