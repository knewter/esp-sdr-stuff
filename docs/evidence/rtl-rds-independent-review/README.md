# Independent RTL-SDR FM/RDS review

**Pass for the selected 101.1 MHz FM/RDS application.** An agent who did not
author the RTL trial independently verified the retained private input hashes,
rebuilt FM multiplex audio from the original IQ, reran both inputs through the
pinned no-FEC decoder, and counted the actual output without importing the
trial's summary function. Both outputs reproduced byte for byte. This review
opened no receiver, USB device or serial port; it verifies recorded reception
and reproducibility, rather than adding a second physical capture.

The reviewed trial is commit `cac792ca92bf2e67801a390385c3d07c82c415b8`.
Its [receiver settings, sanitized driver log, original groups and timing](../rtl-rds-trial/README.md)
remain the physical evidence. The independent [receipt](receipt.json) and
[offline review program](review.py) record this review's checks.

| Input | Emitted groups | Complete groups | Accepted blocks | Missing blocks | Direct accepted block-A PI |
|---|---:|---:|---:|---:|---:|
| Retained IQ → rebuilt MPX | 41 | 30 | 149 | 15 | 40 × `0x9250` |
| Fresh trial's retained MPX | 317 | 245 | 1,163 | 105 | 297 × `0x9250` |

All counts include partially decoded emitted groups. They exclude groups the
decoder did not emit and periods without synchronization. They establish no
overall packet-success percentage, USB continuity guarantee or antenna gain.
The direct PI counts use block A itself, excluding inherited `pi` fields in
partial groups. The live output also reproduces the published RadioText exactly.

## Source and integrity checks

The original IQ, retained WAV and live signed-16 MPX hashes all match their
published SHA-256 values. The rebuilt WAV matches the original WAV's hash.
The redsea binary and loaded liquid-dsp library hashes match provenance;
their tracked source checkouts are clean at commits
`4cc27df9939798e800c4ff7cb484be6d9bf68b4d` and
`10041f70cebbe3b97887e75bb41e48b73dda1b23`, respectively. Decoder runs exit 0
with empty stderr. Raw IQ and audio, and duplicate decoder output, remain in
ignored `.scratch/`; this review publishes hashes and metadata.

The pinned [option parser](https://github.com/windytan/redsea/blob/4cc27df9939798e800c4ff7cb484be6d9bf68b4d/src/options.cc#L224)
disables `use_fec` for `--no-fec` with these MPX/WAV inputs. The
[block synchronizer](https://github.com/windytan/redsea/blob/4cc27df9939798e800c4ff7cb484be6d9bf68b4d/src/block_sync.cc#L270)
calculates the 26-bit block's ten-bit syndrome and compares its offset with
the expected A/B/C/C′/D position. A mismatching block cannot pass via burst
correction with FEC disabled. The
[raw-group formatter](https://github.com/windytan/redsea/blob/4cc27df9939798e800c4ff7cb484be6d9bf68b4d/src/group.cc#L155)
prints accepted 16-bit data words and substitutes `----` for missing blocks.
This confirms checkword validation inside redsea. The public words omit the
ten check bits, so this review does **not** claim a separate external CRC
recomputation, error-free contents or cryptographic transmitter identity.

## Known-source attribution and task 1.2

The independently checked [station-owned WXJC homepage](https://www.wxjcradio.com/)
identifies WXJC Radio / Truth 101.1 (checked 2026-10-01). Independent base-26
arithmetic maps PI `0x9250` to `WXJC`, following the pinned
[RBDS implementation](https://github.com/windytan/redsea/blob/4cc27df9939798e800c4ff7cb484be6d9bf68b4d/src/tables.cc#L343).
Repeated accepted block-A identity, the public frequency match and decoded
broadcast metadata support attribution to that known broadcast station.

This supports comparison-proposal task **1.2's selected-application result**:
the existing RTL-SDR Blog V4 receive path is functionally adequate for FM/RDS
on this station at this time, with published settings and actual decoder output.
The exact antenna model, physical attachment and orientation were not inspected;
do not mark an antenna-inventory requirement verified or describe an identified
antenna as tested. If task 1.2 is interpreted to require that additional physical
inspection, its antenna clause remains open. The result does not establish
sensitivity, calibrated RF level, all-band antenna suitability, an ESP32
application result, or a common-signal receiver comparison.

## Reproduction

Run from the firmware-tools worktree, choosing a new ignored scratch directory:

```sh
python3 docs/evidence/rtl-rds-independent-review/review.py \
  --rtl-worktree ../rtl-evaluation \
  --scratch .scratch/rds-independent-review \
  --receipt docs/evidence/rtl-rds-independent-review/receipt.json
```

The script uses only retained files and the existing pinned decoder. It asserts
source and binary hashes, reproduced WAV/output equality and independently
counted results; it never invokes `rtl_fm` or another hardware command. Its
scratch directory must be new to preserve prior review artifacts.
