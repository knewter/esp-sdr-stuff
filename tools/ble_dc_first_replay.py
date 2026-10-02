#!/usr/bin/env python3
"""Paired saved-IQ replay; subtract the whole raw mean before the old decoder.

No hardware, changed packet checks, search expansion or emission denominator.
CRC-valid matches remain candidates for independent whole-window replay.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import time
import zlib

import numpy as np
import ble_decode_iq as core
from esp_sdr_capture import unpack

ROOT = Path(__file__).resolve().parents[1]
METHOD = 'raw-capture-mean-before-original-decoder-v1'


def decode_dc_first(iq, rate, channel, marker_ad=core.MARKER_AD,
                    frequency_translation_hz=0, refine=False):
    raw = np.asarray(iq)
    if raw.ndim != 1 or not raw.size or not np.isfinite(raw).all():
        raise ValueError('finite, nonempty one-dimensional IQ required')
    return core.decode_iq(raw - raw.mean(), rate, channel, marker_ad,
                          frequency_translation_hz, refine)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(captures, private, bits, frequency_mhz):
    rows = list(csv.DictReader(captures.open()))
    if not rows or len(rows) > 10000:
        raise ValueError('capture table empty or over budget')
    result = []
    indices = set()
    expected_bytes = 32760 if bits == 8 else 40950
    for row in rows:
        index = int(row['capture_index'])
        if index < 0 or index in indices:
            raise ValueError('invalid or duplicate capture index')
        indices.add(index)
        payload = (private / f'iq-{index:04d}.bin').read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        crc = f'{zlib.crc32(payload):08x}'
        if (len(payload) != expected_bytes or int(row['returned_samples']) != 16380
                or digest != row['private_payload_sha256']
                or crc != row['expected_crc32'].lower()
                or crc != row['actual_crc32'].lower()
                or row['crc_ok'] != 'True' or row['sample_count_ok'] != 'True'):
            raise ValueError(f'capture {index}: saved input integrity failed')
        lo = int(row.get('frequency_mhz', frequency_mhz))
        translation = (lo - 2402) * 1000000
        iq = unpack(payload, 16380, bits)
        before = core.decode_iq(iq, 16000000, 37, core.MARKER_AD, translation, True)
        after = decode_dc_first(iq, 16000000, 37, core.MARKER_AD, translation, True)
        result.append(dict(capture_index=index, payload_sha256=digest,
                           input_bytes=len(payload), verified_crc32=crc,
                           frequency_translation_hz=translation,
                           original_frames=before, dc_first_frames=after))
    return result


def counts(rows, field):
    return dict(crc_valid_owned_candidates=sum(
                    f['status'] == 'valid_owned' for r in rows for f in r[field]),
                crc_valid_other_candidates_redacted=sum(
                    f['status'] == 'valid_other_redacted' for r in rows for f in r[field]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', type=Path, required=True)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bits', type=int, choices=(8, 10), required=True)
    parser.add_argument('--frequency-mhz', type=int, default=2401)
    args = parser.parse_args()
    output = args.output.resolve()
    if (output.exists() or not output.is_relative_to(ROOT / '.scratch')
            or output == ROOT / '.scratch'):
        parser.error('fresh ignored scratch output required; candidates need independent review')
    started = time.monotonic()
    rows = replay(args.captures, args.private, args.bits, args.frequency_mhz)
    result = dict(schema=1, method=METHOD, source_hashes={
                        'tools/ble_dc_first_replay.py': sha(Path(__file__)),
                        'tools/ble_decode_iq.py': sha(Path(core.__file__)),
                        'tools/esp_sdr_capture.py': sha(ROOT / 'tools/esp_sdr_capture.py')},
                  capture_csv_sha256=sha(args.captures), captures_analyzed=len(rows),
                  bits_per_component=args.bits, samples_per_capture=16380,
                  nominal_rate_hz=16000000, channel=37,
                  blind_receiver_refinement=core.REFINEMENT,
                  original_counts=counts(rows, 'original_frames'),
                  dc_first_counts=counts(rows, 'dc_first_frames'), captures=rows,
                  runtime_seconds=time.monotonic()-started,
                  transmitted_event_denominator=None, RF_gate_closed=False,
                  scope='Saved physical IQ paired processing; not a new live trial',
                  limits='CRC-valid candidates require independent complete-window, '
                         'protected-PDU and exact-AD replay. Original nulls remain '
                         'unchanged; no source cause, detection rate or Trial B admission.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('captures_analyzed', 'original_counts',
                                          'dc_first_counts', 'runtime_seconds')}))


if __name__ == '__main__':
    main()
