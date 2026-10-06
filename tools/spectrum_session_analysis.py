#!/usr/bin/env python3
"""Per-pair decoded-packet location for controlled spectrum sessions 003+.

For each channel and pair capture (a-ch{N}-p{n}), decode every window with
ble_extended_primary over a translation grid, then locate the channel with
spectrum_decoded_location.locate. A channel confirms when all three pairs
decode at least one owned packet in ON windows and none in OFF windows.
No hardware access.
"""
import argparse
import json
from pathlib import Path

from ble_extended_primary import main as decode
from spectrum_decoded_location import locate

CHANNELS = ((37, 2402), (38, 2426), (39, 2480))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--session', type=Path, required=True)
    cli.add_argument('--owned-reference', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    cli.add_argument('--grid-khz', type=int, nargs='+', default=list(range(-200, -4201, -400)))
    cli.add_argument('--pairs', type=int, default=3)
    a = cli.parse_args()
    out = {'grid_khz': a.grid_khz, 'channels': {}}
    for ch, nominal in CHANNELS:
        pairs = {}
        for n in range(1, a.pairs+1):
            stem = a.session/f'a-ch{ch}-p{n}'
            if not (stem/'results.json').exists():
                continue
            decodes = []
            for k in a.grid_khz:
                path = a.session/f'a-ch{ch}-p{n}-decode{k}.json'
                if not path.exists():
                    decode(['--input', str(a.session/f'a-ch{ch}-p{n}-raw'), '--output', str(path),
                            '--owned-reference', str(a.owned_reference), '--rate', '16000000',
                            '--frequency-translation-hz', str(k*1000), '--channel', str(ch), '--accept-chsel'])
                decodes.append((path, k*1000))
            result = locate(stem, a.session/f'a-ch{ch}-p{n}-source.jsonl', decodes, nominal-1, nominal)
            pairs[f'p{n}'] = {k: result[k] for k in ('source_cycles', 'controller_counted_events', 'owned_off_total',
                                                     'median_carrier_mhz', 'offset_from_nominal_khz', 'carrier_spread_khz')}
            pairs[f'p{n}']['owned_on'] = sum(p['owned_on'] for p in result['pairs'])
        if pairs:
            out['channels'][f'ch{ch}'] = {'pairs': pairs, 'confirmed': len(pairs) == a.pairs and all(
                p['owned_on'] >= 1 and p['owned_off_total'] == 0 for p in pairs.values())}
    out['task_1_2_satisfied'] = len(out['channels']) == 3 and all(c['confirmed'] for c in out['channels'].values())
    a.output.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
