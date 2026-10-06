#!/usr/bin/env python3
"""Narrowband burst detection in ESP32-C3 snapshots (C3 burst session 001).

The C3 snapshot (16380 samples at 80 MS/s, 204.75 us) is too short to hold a
complete 184 us owned packet in most overlaps, so this counts burst energy
instead of decoding. Fixed before data collection:

- 64-point Hann FFT frames (0.8 us, 1.25 MHz bins), no overlap;
- per-bin power smoothed over 25 frames (20 us);
- each window is scaled by its median power in 2380-2392 MHz (hardware AGC
  compensation), then each bin is referenced to its median smoothed power
  over every window in the capture (bursts occupy few windows);
- a window detects when some time/bin inside the search band is >= 10 dB
  above its reference AND >= 6 dB above both neighbour bands (4-6 MHz below
  and above, same time), which rejects 20 MHz-wide Wi-Fi.

ON/OFF classification uses the counted source spans and guards from
ble_hitrate_report. No hardware access.
"""
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from ble_extended_primary import unpack
from ble_hitrate_report import classify, merge, source_spans

RATE = 80_000_000
FFT = 64
SMOOTH = 25
THRESHOLD_DB = 10.0
CONTRAST_DB = 6.0
NEIGHBOUR_MHZ = (4.0, 6.0)
AGC_REFERENCE_MHZ = (2380.0, 2392.0)


def smoothed_power(iq):
    x = np.asarray(iq, dtype=np.complex64)
    x = x - x.mean()
    frames = x[:len(x)//FFT*FFT].reshape(-1, FFT)*np.hanning(FFT)
    power = np.abs(np.fft.fftshift(np.fft.fft(frames, axis=1), axes=1))**2
    kernel = np.ones(SMOOTH)/SMOOTH
    return np.apply_along_axis(lambda c: np.convolve(c, kernel, mode='valid'), 0, power)


def bin_offsets_mhz():
    return np.fft.fftshift(np.fft.fftfreq(FFT, 1/RATE))/1e6


def window_statistics(powers, lo_mhz, band_mhz):
    """Per window: peak in-band excess over reference, contrast, and frequency."""
    freqs = lo_mhz+bin_offsets_mhz()
    # Hardware AGC moves the level between windows; each window is first
    # scaled by its own median in a quiet passband slice clear of ch37 and
    # Wi-Fi channel 1.
    quiet = (freqs >= AGC_REFERENCE_MHZ[0]) & (freqs <= AGC_REFERENCE_MHZ[1])
    powers = [p/np.median(p[:, quiet]) for p in powers]
    reference = np.median(np.stack([np.median(p, axis=0) for p in powers]), axis=0)
    band = np.flatnonzero((freqs >= band_mhz[0]) & (freqs <= band_mhz[1]))
    out = []
    for p in powers:
        excess = 10*np.log10(p/reference)
        best = None
        for b in band:
            lower = (freqs >= freqs[b]-NEIGHBOUR_MHZ[1]) & (freqs <= freqs[b]-NEIGHBOUR_MHZ[0])
            upper = (freqs >= freqs[b]+NEIGHBOUR_MHZ[0]) & (freqs <= freqs[b]+NEIGHBOUR_MHZ[1])
            side = np.maximum(excess[:, lower].mean(axis=1), excess[:, upper].mean(axis=1))
            contrast = excess[:, b]-side
            ok = (excess[:, b] >= THRESHOLD_DB) & (contrast >= CONTRAST_DB)
            t = int(np.argmax(np.where(ok, excess[:, b], -np.inf))) if ok.any() else int(np.argmax(excess[:, b]))
            item = (bool(ok.any()), float(excess[t, b]), float(contrast[t]), float(freqs[b]), t)
            if best is None or item[:2] > best[:2]:
                best = item
        out.append({'detected': best[0], 'peak_excess_db': best[1], 'contrast_db': best[2],
                    'peak_frequency_mhz': best[3], 'peak_time_us': best[4]*FFT/RATE*1e6})
    return out


def fisher_one_sided(a, b, c, d):
    """P(X >= a) for the 2x2 table [[a, b], [c, d]] with fixed margins."""
    n, r, k = a+b+c+d, a+b, a+c
    comb = math.comb
    return sum(comb(r, x)*comb(n-r, k-x) for x in range(a, min(r, k)+1))/comb(n, k)


def analyse(capture, private, source_jsonl, lo_mhz, band_mhz, guard_ms=100):
    capture, private = Path(capture), Path(private)
    results = json.loads((capture/'results.json').read_text())
    anchor = results['series_start_monotonic_ns']
    rows = [r for r in csv.DictReader((capture/'snapshots.csv').open()) if r['status'] == 'ok']
    name = lambda r: f"iq-{r['rate_hz']}-{r['bits_per_component']}-{int(r['attempt']):04d}.bin"
    powers = [smoothed_power(unpack((private/name(r)).read_bytes(), int(r['returned_samples']), 8)) for r in rows]
    stats = window_statistics(powers, lo_mhz, band_mhz)
    records = [json.loads(l) for l in Path(source_jsonl).read_text().splitlines() if l.startswith('{')]
    spans, counted = source_spans(records)
    merged = merge(spans)
    guard = int(guard_ms*1e6)
    windows = []
    for r, s in zip(rows, stats):
        bracket = (anchor+int(float(r['command_start_relative_ms'])*1e6), anchor+int(float(r['header_received_relative_ms'])*1e6))
        windows.append({'window': name(r), 'state': classify(bracket, merged, guard), **s})
    return windows, {'source_cycles': len(spans), 'controller_counted_events': counted}


def summary(windows):
    on = [w for w in windows if w['state'] == 'on']
    off = [w for w in windows if w['state'] == 'off']
    a, c = sum(w['detected'] for w in on), sum(w['detected'] for w in off)
    return {'on_windows': len(on), 'on_detected': a, 'off_windows': len(off), 'off_detected': c,
            'other_windows': len(windows)-len(on)-len(off),
            'fisher_one_sided_p': fisher_one_sided(a, len(on)-a, c, len(off)-c) if on and off else None,
            'on_detected_frequencies_mhz': sorted(w['peak_frequency_mhz'] for w in on if w['detected']),
            'off_detected_frequencies_mhz': sorted(w['peak_frequency_mhz'] for w in off if w['detected'])}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--session', type=Path, required=True)
    cli.add_argument('--private-root', type=Path, required=True)
    cli.add_argument('--pairs', type=int, default=3)
    cli.add_argument('--lo-mhz', type=float, default=2396)
    cli.add_argument('--band-mhz', type=float, nargs=2, default=[2399, 2409])
    cli.add_argument('--output', type=Path, required=True)
    a = cli.parse_args()
    out, everything = {'thresholds': {'threshold_db': THRESHOLD_DB, 'contrast_db': CONTRAST_DB, 'fft': FFT,
                                      'smooth_frames': SMOOTH, 'band_mhz': a.band_mhz, 'lo_mhz': a.lo_mhz}, 'pairs': []}, []
    for n in range(1, a.pairs+1):
        cap = a.session/f'p{n}'
        if not (cap/'results.json').exists():
            continue
        windows, source = analyse(cap, a.private_root/f'p{n}-raw', a.session/f'p{n}-source.jsonl', a.lo_mhz, a.band_mhz)
        everything += windows
        out['pairs'].append({'pair': n, **source, **summary(windows)})
    out['combined'] = summary(everything)
    out['confirmed'] = bool(out['pairs']) and len(out['pairs']) == a.pairs and all(p['on_detected'] >= 1 for p in out['pairs']) \
        and out['combined']['fisher_one_sided_p'] is not None and out['combined']['fisher_one_sided_p'] < 0.01
    a.output.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'pairs'}, indent=1))


if __name__ == '__main__':
    main()
