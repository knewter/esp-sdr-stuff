# Zero-counter RF discriminator: inconclusive

All **262 physical snapshots** passed independent waveform SHA-256, byte-length,
sample-count and transport-CRC checks. The pinned blind decoder found **zero
complete CRC-valid exact owned packets** in the 220-snapshot original run and
42-snapshot supplemental segment. One access-address candidate failed CRC; it
does not establish owned reception. This null result cannot distinguish no
emission from sparse sampling or receiver/decoder limitations.

All ten source episodes were retained. Native source and independent monitor
records agree on handle 1, accepted 20 ms interval, legacy nonconnectable LE1M,
channel 37, exact owned AD, five-second duration, nonzero requested maximum
255, actual termination status `0x3C`, and **controller-completed count 0**.
Enable and handle-specific cleanup commands were acknowledged with status 0.
The helper's original `trial_failed` status and exit code 2 remain intact.
**Actual RF emission count is unknown**; zero is the controller field, not an
independently observed RF count. No recovery rate or ≥100 counted-event gate is
accepted. This diagnostic does not change the earlier [four verified BlueZ
receptions](../ble-owned-decoding/README.md) or [one controls-trial
reception](../ble-controls-decoding/README.md).

## Schedule limitation

The original run had 5.658144 seconds before the first enable, but only
**8.620010 seconds** after final source closure. It failed the prospectively
required **more-than-ten-second continuous tail**. The original
[schedule receipt](schedule-receipt.json) remains unchanged.

The separate supplemental segment lasted 15.316332 seconds and began after a
**54.217849-second gap** from the original segment. Its 42 snapshots are OFF
controls, replayed separately with their original timestamps and local indices.
The extension does not repair the continuous-tail failure; see
[schedule extension](schedule-extension.json). Every original capture and
episode, including diagnostic failures and boundary captures, is preserved.

## Blind replay and phase accounting

The fixed receiver settings were LO 2401 MHz, filter 20 MHz, manual gain 48,
nominal 16 MS/s, 8-bit I/Q components and 16,380 complex samples per snapshot.
Replay used channel 37, −1 MHz digital translation, and the full committed
13×17×37 blind AA-trained search. Decoder SHA-256:
`834fdd78e3221d0625eaa7cf1059b9bd59d3b8b9fa929578f2555bff64130128`.
No known-marker bit trained, repaired or selected a receiver hypothesis; no
search bound was expanded after inspecting this dataset. The
[prospective protocol](../../research/ble-zero-counter-rf-protocol.md) records
the exact decoder revision and all search bounds.

A source-associated packet would require its entire capture request-response
bracket inside both source and monitor enable acknowledgements plus 100 ms,
through their termination observations minus 100 ms; the report uses the more
conservative of the two receipts. It would also require exact whole AD match,
strict CRC24, type 2/length 22, and complete nominal 256 µs packet bounds.
Hypothesis duplicates count once; incompatible distinct owned clusters within
one 1.024 ms snapshot cannot count as two source events. All candidate statuses
were retained, including the unowned failed CRC.

| Episode | Guarded snapshots | AA-candidate snapshots | Verified owned packets |
| --- | ---: | ---: | ---: |
| zero-counter-01 | 13 | 0 | 0 |
| zero-counter-02 | 12 | 0 | 0 |
| zero-counter-03 | 13 | 0 | 0 |
| zero-counter-04 | 12 | 0 | 0 |
| zero-counter-05 | 12 | 0 | 0 |
| zero-counter-06 | 13 | 1, CRC failed | 0 |
| zero-counter-07 | 12 | 0 | 0 |
| zero-counter-08 | 13 | 0 | 0 |
| zero-counter-09 | 12 | 0 | 0 |
| zero-counter-10 | 13 | 0 | 0 |

The original segment additionally contains 66 OFF snapshots and 29 excluded
boundary snapshots; the supplemental segment adds 42 OFF snapshots. These are
snapshot/phase counts, not emitted-event counts or continuous RF coverage.

## Receipts and reproduction

[Analysis](analysis.json) contains every episode's original diagnostic status,
native/monitor matching receipts, input hashes, per-phase counts, separate
segment boundaries and the failed schedule gate. [Main decoder
manifest](decoder-main.json) and [supplemental decoder manifest](decoder-tail.json)
include every capture's hash, blind-search descriptor, source phase, full host
timestamps and redacted candidate results. Raw IQ remains private because it
can contain addresses; there is no positive packet plot for this null result.

Run `python3 tools/ble_zero_counter_report.py --input PRIVATE-DATASET --output
FRESH-ANALYSIS-DIRECTORY` to reproduce all raw integrity checks, both complete
blind replays, and their source/monitor joins. The reporter records executed
script hashes and repository revision. Eight metadata-only diagnostic
regression cases verify full-response timing guards, failed-tail/gap retention,
source/monitor count/handle/data/cleanup mismatches, marker/PDU/window gates,
hypothesis deduplication, incompatible clusters and unchanged search bounds.
These tests prove accounting behavior, not reception.

See [earlier source-only diagnostics](../ble-duration-source-diagnostics/README.md)
for the controller-count investigation and [verified original-firmware
restoration](../zero-counter-restoration/README.md) for the hardware release.
The root-owned provenance receipts record monitor readiness before receiver
startup; monotonic packet records alone do not timestamp that readiness event.
