#!/usr/bin/env python3
"""Offline independent RDS receipt; never invokes a receiver or opens a device."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy import signal
from scipy.io import wavfile


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def counts(data):
    rows = [json.loads(line) for line in data.splitlines() if line.strip()]
    valid = complete = 0
    direct = Counter()
    for row in rows:
        blocks = row['raw_data'].split()
        assert len(blocks) == 4
        assert all(b == '----' or (len(b) == 4 and all(c in '0123456789ABCDEF' for c in b)) for b in blocks)
        valid += sum(b != '----' for b in blocks)
        complete += all(b != '----' for b in blocks)
        if blocks[0] != '----':
            direct['0x' + blocks[0]] += 1
    return {'emitted_groups': len(rows), 'complete_four_block_groups': complete,
            'valid_blocks_in_emitted_groups': valid, 'missing_blocks_in_emitted_groups': len(rows)*4-valid,
            'direct_valid_block_a_pi_counts': dict(direct),
            'callsigns_in_decoder_output': sorted({r['callsign'] for r in rows if 'callsign' in r}),
            'radiotext_values': sorted({r['radiotext'] for r in rows if 'radiotext' in r})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rtl-worktree', required=True, type=Path)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=False)
    base = args.rtl_worktree
    private = base/'.scratch'
    evidence = base/'docs/evidence/rtl-rds-trial'
    provenance = json.loads((evidence/'provenance.json').read_text())
    decoder = private/'redsea-build/redsea'
    receipt = {'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'hardware_access': False,
               'author_tools_imported': False, 'inputs': {}, 'runs': {}, 'source_checks': {}}
    for name, expected in [('fm101.iq', '2f60d138da86399ed28ed55d2290da9277f98d13c552604a0cf3e16aea16d555'),
                           ('fm101-rds-repro.wav', 'fc5ff1496dc246e765f3f7088f0a4fadd0738ef68ca2dd0d64d11caaf6e66b7c'),
                           ('fm101-live-mpx.pcm', '5f189dde13c3551080d0eb3af4ea6801a6f9d8187b379a92d31b848b126a51d0')]:
        path = private/name
        actual = sha(path)
        assert actual == expected, name
        receipt['inputs'][name] = {'bytes': path.stat().st_size, 'sha256': actual, 'matches_published': True}
    assert sha(decoder) == provenance['sources']['redsea']['binary_sha256']
    receipt['decoder_binary_sha256'] = sha(decoder)
    library = private/'rds-prefix/lib/libliquid.so.1'
    assert sha(library) == provenance['sources']['liquid_dsp']['library_sha256']
    receipt['liquid_library_sha256'] = sha(library)
    for name, folder in [('redsea', 'redsea-src'), ('liquid_dsp', 'liquid-src')]:
        source = private/folder
        commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True)
        assert commit == provenance['sources'][name]['commit'] and not dirty
        receipt['source_checks'][name] = {'commit': commit, 'tracked_checkout_clean': True}
    # Recreate MPX without importing the trial author’s tool. Same documented
    # DSP procedure is necessary for a byte-for-byte reproduction comparison.
    u8 = np.fromfile(private/'fm101.iq', dtype=np.uint8)
    z = (u8[0::2].astype(np.float32)-127.5)/128 + 1j*(u8[1::2].astype(np.float32)-127.5)/128
    z *= np.exp(-2j*np.pi*100000/1024000*np.arange(z.size))
    channel = signal.resample_poly(z, 1, 4, window=signal.firwin(255, 90000, fs=1024000))
    fm = np.angle(channel[1:]*channel[:-1].conjugate())*256000/(2*np.pi)
    fm = fm[25600:]
    rebuilt = args.scratch/'rebuilt-mpx.wav'
    wavfile.write(rebuilt, 256000, np.rint(fm/np.max(np.abs(fm))*30000).astype(np.int16))
    assert sha(rebuilt) == receipt['inputs']['fm101-rds-repro.wav']['sha256']
    receipt['retained_mpx_rebuilt'] = {'sha256': sha(rebuilt), 'bytes': rebuilt.stat().st_size, 'byte_identical': True}
    common = ['--no-fec', '--show-raw', '--rbds', '--bler', '--time-from-start']
    for name, path, mode in [('retained', rebuilt, ['-f', str(rebuilt)]),
                             ('live', private/'fm101-live-mpx.pcm', ['--input', 'mpx', '-r', '171000'])]:
        with path.open('rb') as input_stream:
            run = subprocess.run([str(decoder.resolve()), *mode, *common], stdin=input_stream, capture_output=True, timeout=120)
        assert run.returncode == 0 and not run.stderr
        (args.scratch/(name+'.ndjson')).write_bytes(run.stdout)
        published = (evidence/(name+'-decoder.ndjson')).read_bytes()
        assert run.stdout == published, name
        summary = counts(run.stdout)
        original = json.loads((evidence/(name+'-trial.json')).read_text())['decode_summary']
        assert all(summary[k] == original[k] for k in summary), name
        receipt['runs'][name] = {'returncode': run.returncode, 'stderr_bytes': len(run.stderr),
                               'flags': common, 'input_mode': 'wav' if name == 'retained' else 'signed16_mpx_171000',
                               'ndjson_sha256': hashlib.sha256(run.stdout).hexdigest(),
                               'byte_identical_to_published': True, 'counts': summary}
    # Independent arithmetic interpretation of ordinary four-letter RBDS PI.
    pi = 0x9250-0x54A8
    call = 'W'+''.join(chr(65+(pi//divisor)%26) for divisor in (26*26, 26, 1))
    assert call == 'WXJC'
    receipt['pi_arithmetic'] = {'pi': '0x9250', 'w_offset': '0x54A8', 'base26_suffix': call[1:], 'callsign': call}
    args.receipt.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
