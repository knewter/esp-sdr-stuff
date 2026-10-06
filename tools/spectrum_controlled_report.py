#!/usr/bin/env python3
"""Offline report for controlled spectrum session 001 (no hardware access).

Implements docs/research/spectrum-controlled-001-protocol.md:
A. per-channel source-on/off pairs: burst-gated ON-minus-OFF spectral excess,
   its peak offset from the LO, background power and owned decodes;
B. filter/gain sweep: AC power, ADC endpoint (clipping) fraction, spectral
   width of the burst-gated spectrum and owned decodes;
C. FM extended tuning: strongest narrow peak per LO, compared with an
   independently recorded RTL-SDR spectrum.
Levels are relative ADC codes; nothing here is calibrated.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from ble_hitrate_report import classify, merge, source_spans
from esp_sdr_capture import unpack

RATE = 16_000_000
SAMPLES = 16380
NFFT = 1024
BIN_HZ = RATE/NFFT
DC_GUARD_BINS = 3


def load_capture(folder):
    folder = Path(folder)
    results = json.loads((folder/'results.json').read_text())
    rows = [r for r in csv.DictReader((folder/'snapshots.csv').open()) if r['status'] == 'ok']
    raw = Path(str(folder)+'-raw')
    return results, rows, raw


def iq_of(raw, row):
    name = f"iq-{row['rate_hz']}-{row['bits_per_component']}-{int(row['attempt']):04d}.bin"
    return unpack((raw/name).read_bytes(), SAMPLES, 8)


def block_spectra(iq):
    """Hann-windowed power spectra of each 1,024-sample block (fftshifted)."""
    x = iq[:len(iq)//NFFT*NFFT]-iq.mean()
    blocks = x.reshape(-1, NFFT)*np.hanning(NFFT)
    return np.abs(np.fft.fftshift(np.fft.fft(blocks, axis=1), axes=1))**2, np.sum(np.abs(blocks)**2, axis=1)


def gated_spectrum(iq):
    """Spectrum of the most energetic block: catches a sparse burst if present."""
    spectra, energy = block_spectra(iq)
    return spectra[int(np.argmax(energy))]


def mean_spectrum(iq):
    return block_spectra(iq)[0].mean(axis=0)


def offsets_hz():
    return (np.arange(NFFT)-NFFT//2)*BIN_HZ


def peak_offset(spectrum_db, exclude_dc=True):
    s = spectrum_db.copy()
    if exclude_dc:
        s[NFFT//2-DC_GUARD_BINS:NFFT//2+DC_GUARD_BINS+1] = -np.inf
    i = int(np.argmax(s))
    return float(offsets_hz()[i]), float(s[i])


def decodes(decode_json):
    if decode_json is None or not Path(decode_json).exists():
        return None
    d = json.loads(Path(decode_json).read_text())
    return {c['capture_filename']: sum(f['status'] == 'valid_owned_primary' for f in c['frames']) for c in d['captures']}


def part_a(folder, source_jsonl, decode_json, expected_offset_hz, guard_ms=100):
    results, rows, raw = load_capture(folder)
    anchor = results['series_start_monotonic_ns']
    records = [json.loads(line) for line in Path(source_jsonl).read_text().splitlines() if line.startswith('{"kind"') or line.startswith('{')]
    spans, counted = source_spans(records)
    merged = merge(spans)
    owned = decodes(decode_json)
    guard = int(guard_ms*1e6)
    pairs = []
    for index, (low, high) in enumerate(merged):
        previous_high = merged[index-1][1] if index else anchor
        on, off = [], []
        for row in rows:
            start = anchor+float(row['command_start_relative_ms'])*1e6
            end = anchor+float(row['header_received_relative_ms'])*1e6
            if low+guard <= start and end <= high-guard:
                on.append(row)
            elif previous_high+guard <= start and end <= low-guard:
                off.append(row)
        if not on or not off:
            pairs.append({'pair': index+1, 'on_windows': len(on), 'off_windows': len(off), 'confirmed': False})
            continue
        on_spec = np.mean([gated_spectrum(iq_of(raw, r)) for r in on], axis=0)
        off_spec = np.mean([gated_spectrum(iq_of(raw, r)) for r in off], axis=0)
        excess_db = 10*np.log10(on_spec/off_spec)
        offset, excess = peak_offset(excess_db)
        name = lambda r: f"iq-{r['rate_hz']}-{r['bits_per_component']}-{int(r['attempt']):04d}.bin"
        pairs.append({'pair': index+1, 'on_windows': len(on), 'off_windows': len(off),
                      'excess_peak_offset_mhz': offset/1e6, 'excess_peak_db': excess,
                      'background_off_power_db': float(10*np.log10(off_spec.sum())),
                      'owned_decodes_on': None if owned is None else sum(owned.get(name(r), 0) for r in on),
                      'owned_decodes_off': None if owned is None else sum(owned.get(name(r), 0) for r in off),
                      'confirmed': abs(offset-expected_offset_hz) <= 2e6})
    return {'source_cycles': len(spans), 'controller_counted_events': counted, 'merged_on_spans': len(merged),
            'expected_offset_mhz': expected_offset_hz/1e6, 'pairs': pairs,
            'channel_confirmed': len(pairs) >= 3 and all(p['confirmed'] for p in pairs)}


def part_b(folder, decode_json):
    results, rows, raw = load_capture(folder)
    power = np.array([float(r['ac_power_codes_squared']) for r in rows])
    endpoint = np.array([float(r['component_endpoint_fraction']) for r in rows])
    spec = np.mean([gated_spectrum(iq_of(raw, r)) for r in rows], axis=0)
    db = 10*np.log10(spec)
    offset, peak = peak_offset(db)
    floor = float(np.median(db))
    above = np.flatnonzero(db >= peak-10)
    owned = decodes(decode_json)
    return {'settings': results['settings'], 'windows': len(rows),
            'ac_power_mean': float(power.mean()), 'ac_power_p99': float(np.percentile(power, 99)),
            'endpoint_fraction_mean': float(endpoint.mean()), 'endpoint_fraction_max': float(endpoint.max()),
            'gated_peak_offset_mhz': offset/1e6, 'gated_peak_over_floor_db': peak-floor,
            'gated_width_10db_mhz': float((above.max()-above.min()+1)*BIN_HZ/1e6),
            'owned_decodes': None if owned is None else sum(owned.values())}


def part_c(folder):
    results, rows, raw = load_capture(folder)
    spec = np.mean([mean_spectrum(iq_of(raw, r)) for r in rows], axis=0)
    db = 10*np.log10(spec)
    offset, peak = peak_offset(db)
    order = np.argsort(np.where(np.abs(np.arange(NFFT)-NFFT//2) > DC_GUARD_BINS, db, -np.inf))[::-1]
    peaks, taken = [], []
    for i in order:
        if all(abs(i-j) > 8 for j in taken):
            taken.append(i); peaks.append({'offset_mhz': float(offsets_hz()[i]/1e6), 'over_median_db': float(db[i]-np.median(db))})
        if len(peaks) == 5:
            break
    return {'lo_mhz': results['settings']['frequency'], 'gain': results['settings']['gain'], 'windows': len(rows),
            'strongest_offset_mhz': offset/1e6, 'strongest_absolute_mhz': results['settings']['frequency']+offset/1e6,
            'strongest_over_median_db': float(peak-np.median(db)), 'top_peaks': peaks}


def rtl_reference(path, center_hz=101_400_000, rate=1_200_000):
    u = np.fromfile(path, dtype=np.uint8).astype(np.float32)-127.5
    iq = (u[0::2]+1j*u[1::2])
    blocks = iq[:len(iq)//4096*4096].reshape(-1, 4096)*np.hanning(4096)
    spec = np.mean(np.abs(np.fft.fftshift(np.fft.fft(blocks, axis=1), axes=1))**2, axis=0)
    db = 10*np.log10(spec+1e-12)
    freqs = center_hz+(np.arange(4096)-2048)*rate/4096
    mask = np.abs(np.arange(4096)-2048) > 20
    i = int(np.argmax(np.where(mask, db, -np.inf)))
    station = int(np.argmin(np.abs(freqs-101_100_000)))
    return {'center_mhz': center_hz/1e6, 'strongest_mhz': float(freqs[i]/1e6),
            'strongest_over_median_db': float(db[i]-np.median(db)),
            'at_101_1_over_median_db': float(db[station]-np.median(db))}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--session', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    cli.add_argument('--board-offset-hz', type=float, default=800_000,
                     help='Measured +0.8 MHz board carrier offset at 2.4 GHz (hit-rate runs)')
    a = cli.parse_args()
    s = a.session
    out = {'schema': 1, 'protocol': 'docs/research/spectrum-controlled-001-protocol.md', 'A': {}, 'B': {}, 'C': {}}
    for ch in (37, 38, 39):
        if (s/f'a-ch{ch}/results.json').exists():
            out['A'][f'ch{ch}'] = part_a(s/f'a-ch{ch}', s/f'a-ch{ch}-source.jsonl', s/f'a-ch{ch}-decode.json',
                                          1_000_000+a.board_offset_hz)
    for cond in ('bw12', 'bw20', 'bw40', 'bw67', 'g16', 'g32', 'g48', 'g64', 'g72'):
        if (s/f'b-{cond}/results.json').exists():
            out['B'][cond] = part_b(s/f'b-{cond}', s/f'b-{cond}-decode.json')
    for cond in ('fm100', 'fm102', 'fm106', 'fm100g48'):
        if (s/f'c-{cond}/results.json').exists():
            out['C'][cond] = part_c(s/f'c-{cond}')
    rtl = s/'c-rtl-101400k-1200k.u8'
    if rtl.exists():
        out['C']['rtl_reference'] = rtl_reference(rtl)
    a.output.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=1)[:4000])


if __name__ == '__main__':
    main()
