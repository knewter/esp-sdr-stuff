#!/usr/bin/env python3
"""Offline BLE detector calibration on spectrum session 005 (CYD, LO 2401, 16 MS/s).
Ground truth: windows with a decoded owned packet whose span overlaps the first
4096 samples (what the device analyses). Negatives: OFF windows (source idle)."""
import ctypes, glob, json, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, 'tools')
from spectrum_decoded_location import owned_packets
from ble_hitrate_report import classify, merge, source_spans
import csv
S = Path('.scratch/spectrum-controlled-005')
tmp = tempfile.mkdtemp()
lib = f'{tmp}/l.so'
subprocess.run(['cc','-O2','-shared','-fPIC','-std=c11','-D_DEFAULT_SOURCE','-o',lib,'firmware/cyd-waterfall/src/cyd_waterfall_logic.c','-lm'],check=True)
c = ctypes.CDLL(lib)
F = ctypes.c_float*240
c.cyd_row_db.argtypes=[ctypes.POINTER(ctypes.c_uint32),ctypes.c_uint,F]
c.cyd_mask_dc.argtypes=[F]
c.cyd_floor_update.restype=ctypes.c_float; c.cyd_floor_update.argtypes=[ctypes.c_float,F,ctypes.c_bool]
MARK = c.cyd_offset_column(3300, 16)
rows = []
for n in (1,2,3):
    cap = S/f'a-ch37-p{n}'
    res = json.loads((cap/'results.json').read_text())
    anchor = res['series_start_monotonic_ns']
    snaps = [r for r in csv.DictReader((cap/'snapshots.csv').open()) if r['status']=='ok']
    recs = [json.loads(l) for l in (S/f'a-ch37-p{n}-source.jsonl').read_text().splitlines() if l.startswith('{')]
    merged = merge(source_spans(recs)[0])
    decodes = [(p, int(Path(p).stem.split('decode')[1])*1000) for p in glob.glob(str(S/f'a-ch37-p{n}-decode*.json'))]
    owned = owned_packets(decodes)
    floor = 0.0; first = True
    for r in snaps:
        name = f"iq-{r['rate_hz']}-{r['bits_per_component']}-{int(r['attempt']):04d}.bin"
        raw = (S/f'a-ch37-p{n}-raw'/name).read_bytes()[:8192]
        words = (ctypes.c_uint32*4096)()
        for k in range(4096):
            i = int.from_bytes(raw[2*k:2*k+1],'little',signed=True)*4
            q = int.from_bytes(raw[2*k+1:2*k+2],'little',signed=True)*4
            words[k] = (i & 0x3ff) | ((q & 0x3ff) << 10)
        db = F(); c.cyd_row_db(words, 4096, db); c.cyd_mask_dc(db)
        floor = c.cyd_floor_update(floor, db, first); first = False
        bracket = (anchor+int(float(r['command_start_relative_ms'])*1e6), anchor+int(float(r['header_received_relative_ms'])*1e6))
        state = classify(bracket, merged, 100_000_000)
        # owned packet overlapping samples 0..4095 (packet ~184 us = 2944 samples after access address - 8 us preamble)
        truth = any(off - 128 < 4096 and off + 2816 > 0 for off, _, _ in owned.get(name, []))
        rows.append({'state': state, 'truth': truth, 'db': list(db), 'floor': floor})
json.dump({'marker': MARK, 'rows': rows}, open('.scratch/cyd-ble-cal/rows.json','w'))
on = [r for r in rows if r['state']=='on']; off=[r for r in rows if r['state']=='off']
print('marker col', MARK, 'rows', len(rows), 'on', len(on), 'off', len(off), 'truth', sum(r['truth'] for r in rows))
