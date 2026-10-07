#!/usr/bin/env python3
"""Per-pair decoded-packet location for controlled spectrum sessions 003+.

locate (default): for each channel and pair capture (a-ch{N}-p{n}), decode
every window with ble_extended_primary over a translation grid, then locate
the channel with spectrum_decoded_location.locate. A channel confirms when all
three pairs decode at least one owned packet in ON windows and none in OFF
windows. --config gives a per-channel LO and grid (session 005+); without it,
every channel uses LO = centre - 1 MHz and --grid-khz.

search: for one channel, decode search captures s-ch{N}-lo{LO} over a grid,
pick the LO with the most owned ON packets (ties: closest to centre - 1 MHz)
and derive the pair grid: the median translation, rounded to 0.2 MHz, +-2.0
MHz in 0.4 MHz steps, kept inside +-7.6 MHz. No hardware access.
"""
import argparse
import json
from pathlib import Path
import statistics

from ble_extended_primary import main as decode
from spectrum_decoded_location import locate

CHANNELS = ((37, 2402), (38, 2426), (39, 2480))
NOMINAL = dict(CHANNELS)


def decode_capture(session, stem, channel, grid_khz, reference, rate=16000000):
    """Decode complete windows of one capture over a grid; return (path, Hz) pairs."""
    # Retained fault fragments share the raw directory, so link the iq-*.bin
    # payloads into their own one.
    iq = session/f'{stem}-iq'
    iq.mkdir(exist_ok=True)
    for f in sorted((session/f'{stem}-raw').glob('iq-*.bin')):
        if not (iq/f.name).exists():
            (iq/f.name).symlink_to(f.resolve())
    decodes = []
    for k in grid_khz:
        path = session/f'{stem}-decode{k}.json'
        if not path.exists():
            decode(['--input', str(iq), '--output', str(path),
                    '--owned-reference', str(reference), '--rate', str(rate),
                    '--frequency-translation-hz', str(k*1000), '--channel', str(channel), '--accept-chsel'])
        decodes.append((path, k*1000))
    return decodes


def pair_grid(lo_mhz, carrier_mhz, rate=16000000):
    centre = round((lo_mhz-carrier_mhz)*5)*200
    grid = [centre+step for step in range(-2000, 2001, 400)]
    guard_khz = rate//2000 - 400   # keep translations inside Nyquist (7600 kHz at 16 MS/s)
    return [k for k in grid if abs(k) <= guard_khz]


def search(a):
    ch, nominal = a.channel, NOMINAL[a.channel]
    results = []
    for lo in a.los:
        stem = f's-ch{ch}-lo{lo}'
        if not (a.session/stem/'results.json').exists():
            continue
        decodes = decode_capture(a.session, stem, ch, a.grid_khz, a.owned_reference, a.rate)
        r = locate(a.session/stem, a.session/f'{stem}-source.jsonl', decodes, lo, nominal, rate=a.rate)
        results.append({'lo_mhz': lo, 'owned_on': sum(p['owned_on'] for p in r['pairs']),
                        'owned_off': r['owned_off_total'], 'median_carrier_mhz': r['median_carrier_mhz']})
    found = [r for r in results if r['owned_on'] > 0]
    out = {'channel': ch, 'search_grid_khz': a.grid_khz, 'captures': results, 'selected': None}
    if found:
        best = max(found, key=lambda r: (r['owned_on'], -abs(r['lo_mhz']-(nominal-1))))
        out['selected'] = {'lo_mhz': best['lo_mhz'], 'grid_khz': pair_grid(best['lo_mhz'], best['median_carrier_mhz'], a.rate)}
    a.output.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out))


def locate_session(a):
    config = json.loads(a.config.read_text()) if a.config else {}
    out = {'grid_khz': a.grid_khz, 'config': config, 'channels': {}}
    for ch, nominal in CHANNELS:
        lo = config.get(str(ch), {}).get('lo_mhz', nominal-1)
        grid = config.get(str(ch), {}).get('grid_khz', a.grid_khz)
        pairs = {}
        for n in range(1, a.pairs+1):
            stem = f'a-ch{ch}-p{n}'
            if not (a.session/stem/'results.json').exists():
                continue
            decodes = decode_capture(a.session, stem, ch, grid, a.owned_reference, a.rate)
            result = locate(a.session/stem, a.session/f'{stem}-source.jsonl', decodes, lo, nominal, rate=a.rate)
            pairs[f'p{n}'] = {k: result[k] for k in ('source_cycles', 'controller_counted_events', 'owned_off_total',
                                                     'median_carrier_mhz', 'offset_from_nominal_khz', 'carrier_spread_khz')}
            pairs[f'p{n}']['owned_on'] = sum(p['owned_on'] for p in result['pairs'])
        if pairs:
            out['channels'][f'ch{ch}'] = {'lo_mhz': lo, 'grid_khz': grid, 'pairs': pairs,
                                          'confirmed': len(pairs) == a.pairs and all(
                                              p['owned_on'] >= 1 and p['owned_off_total'] == 0 for p in pairs.values())}
    out['task_1_2_satisfied'] = len(out['channels']) == 3 and all(c['confirmed'] for c in out['channels'].values())
    a.output.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=1))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('mode', nargs='?', choices=['locate', 'search'], default='locate')
    cli.add_argument('--session', type=Path, required=True)
    cli.add_argument('--owned-reference', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    cli.add_argument('--grid-khz', type=int, nargs='+', default=list(range(-200, -4201, -400)))
    cli.add_argument('--pairs', type=int, default=3)
    cli.add_argument('--config', type=Path, help='locate: JSON {"37": {"lo_mhz": .., "grid_khz": [..]}, ..}')
    cli.add_argument('--channel', type=int, choices=[37, 38, 39], help='search: channel')
    cli.add_argument('--los', type=int, nargs='+', help='search: LOs of the s-ch{N}-lo{LO} captures')
    cli.add_argument('--rate', type=int, choices=[16000000, 40000000], default=16000000)
    a = cli.parse_args()
    if a.mode == 'search':
        if a.channel is None or not a.los:
            cli.error('search needs --channel and --los')
        search(a)
    else:
        locate_session(a)


if __name__ == '__main__':
    main()
