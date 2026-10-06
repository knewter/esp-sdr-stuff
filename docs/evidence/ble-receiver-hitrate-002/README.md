# Counted-source hit rate 002: pre-declared confirmation passes

Recorded 2026-10-05 under the [protocol committed before the run](../../research/ble-receiver-hitrate-002-protocol.md)
(`2f91853`). **The original ESP32 decoded 42 complete owned ADV_EXT_IND
packets in 3,188 source-ON windows and none in 111 source-OFF windows, against
108 expected.** Detection efficiency was **0.39 (95% CI 0.28–0.52)**. All three
declared gates pass, so the [run 001](../ble-receiver-hitrate-001/README.md)
decoder corrections (−1.8 MHz shift, ChSel acceptance) are confirmed on fresh data.

| Accounting | Run 002 | Runs 001 + 002 |
| --- | ---: | ---: |
| Controller-counted events (190 × 255, all `0x43`) | 48,450 | 96,900 |
| Windows ON / OFF | 3,188 / 111 | 4,518 / 257 |
| Owned complete ON / OFF | **42 / 0** | **72 / 0** |
| Owned truncated at a window edge | 2 (47 expected) | 2 |
| Expected complete in ON windows | 108.3 | 153.4 |
| Detection efficiency | 0.39 (0.28–0.52) | 0.47 |
| Events with no window overlap | 48,294 | — |

| Declared gate | Result |
| --- | --- |
| At least 10 complete owned ON frames | 42 |
| Zero owned OFF frames | 0 |
| Efficiency interval overlaps run 001 (0.45–0.95) | overlaps at 0.45–0.52 |

All 3,300 captures passed CRC and sample-count checks with no UART fault, at a
407 ms mean interval. The host was otherwise heavily loaded by unrelated
work, but no project decoding ran during acquisition.

## What it means

When a whole owned LE1M packet lands inside a captured 1 ms window, this board
decodes it roughly 40–50% of the time at this placement. Detection is
dominated by acquisition: only about 0.3% of emitted events overlap any window,
because each 1.02 ms snapshot is followed by about 405 ms of UART transfer.
The two runs' point estimates differ (0.66 vs 0.39). Their intervals only
just overlap, so efficiency may vary between sessions with interference
(Wi-Fi channel 6 traffic is visible nearby) or placement.

## Restoration

The original image was rewritten with the preservation wrapper, then a fresh
full 4 MiB readback matched the baseline (SHA-256 `6e8f0793…0974`). A reset
boot shows the original `hello_world` application on ESP-IDF v5.4-dirty at
160 MHz. This is a reset boot, not an independently observed power cycle.

## Limits

The denominator is controller-completed events, not independently observed
air emissions. The expected count assumes uniform event phase and the
host-bracketed mean spacing. Power is uncalibrated, and there is one
placement and one controller.

Summary: [results.json](results.json). Raw IQ, the private AdvA reference,
source logs, flash reads and the boot log stay under ignored `.scratch/`.
