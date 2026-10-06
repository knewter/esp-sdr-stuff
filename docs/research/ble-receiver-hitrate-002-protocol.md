# Counted-source hit rate 002: pre-declared confirmation

Declared 2026-10-05, before any run 002 data exists. Purpose: confirm the
[run 001](../evidence/ble-receiver-hitrate-001/README.md) result. Run 001's
decoder corrections were chosen after inspecting its data; they are fixed here
in advance.

## Fixed conditions

- Receiver: same board, image `550fade-uart921600`, placement unchanged, LO 2401
  MHz, 16 MS/s, 8-bit, BW 12, hardware gain, 16,380 samples, `--batch-fsync`,
  `--count 3300`.
- Source: `ble_repeat_source_container.py --cycles 190`, started 60 s after the
  capture.
- Host: no concurrent decoding or other project work during acquisition.
- Decoder: `ble_extended_primary.py --frequency-translation-hz -1800000
  --accept-chsel` with the same private owned-AdvA reference. No other
  settings may be tried for the reported result.
- Report: `ble_hitrate_report.py`, guard 100 ms, packet duration from the
  decoded frames.

## Reported outcome and gates

Report every count: ON/OFF windows; owned complete/truncated frames; expected
overlapping, complete and truncated events; misses; and efficiency with a 95%
interval. A capture fault is retained, and the windows completed before it are
analysed.

- **Confirmed:** at least 10 complete owned ON frames, 0 owned OFF frames, and
  an efficiency interval that overlaps run 001's (0.45–0.95).
- **Not confirmed:** any owned OFF frame, or an efficiency interval disjoint
  from run 001's. Either result is published as is.

After acquisition, restore the original image and verify it by a full 4 MiB
readback hash before closing the experiment.
