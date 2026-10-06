# Counted-source hit rate 001: 30 owned packets against 48,450 counted events

Recorded 2026-10-05. **The original ESP32 decoded 30 complete, CRC-valid owned
ADV_EXT_IND packets in 1,330 source-ON snapshots and none in 146 source-OFF
snapshots.** About 45 complete packets were expected to land inside those
windows, giving a detection efficiency of **0.66 (95% CI 0.45–0.95)**.

That figure depends on two decoder corrections chosen **after** inspecting this
run (below). The prospective decoder settings produced **zero** packets.
Treat 0.66 as a strong diagnostic, not a qualified rate, until a pre-declared
confirmation run repeats it.

## Setup

| Part | Setting |
| --- | --- |
| Preservation | Fresh full 4 MiB read equal to the preserved baseline (SHA-256 `6e8f0793…0974`) before install |
| Receiver | ESPARGOS `550fade-uart921600`, LO 2401 MHz, 16 MS/s, 8-bit IQ, BW 12, hardware gain, 16,380-sample (1.02 ms) windows |
| Capture rate | 407 ms mean interval; the new `--batch-fsync` option defers per-file fsync (455 ms each on this disk) to series end |
| Source | Host Intel adapter, raw HCI in the pinned Nix container: extended, non-connectable, zero data, handle 1, ch37 only, LE1M, 20 ms |
| Counting | [`ble_repeat_counted_source.py`](../../../tools/ble_repeat_counted_source.py) re-enables 255-event cycles; **190/190 cycles ended `0x43` with count 255** |
| Schedule | 60 s OFF, 1,193.6 s enabled (24.73 ms mean event spacing), then the capture ended |

The capture stopped at attempt 1,476 on a short UART payload (30,908 of
32,760 bytes). The failed prefix is retained privately. Offline decoding was
running on the host at about that time; the cause is not established. All
1,476 completed windows passed CRC and sample-count checks.

## Results

[`ble_hitrate_report.py`](../../../tools/ble_hitrate_report.py) classifies a
window ON only when its whole host command-to-header bracket lies inside the
enabled span shrunk by 100 ms, and OFF only when it lies at least 100 ms away.

| Decoder condition | ON owned | OFF owned | Note |
| --- | ---: | ---: | --- |
| Prospective: −1 MHz shift, v1 profile | 0 | 0 | 8 access-address candidates in total |
| −1.8 MHz shift, v1 profile | 0 | 0 | 6 CRC-valid frames carry the owned AdvA but set header bit 5 |
| −1.8 MHz shift, `--accept-chsel` | **30** | **0** | all 30 complete inside their windows |

| Accounting (last row) | Value |
| --- | ---: |
| Controller-counted events | 48,450 |
| Expected events overlapping ON windows | 64.9 |
| Expected wholly inside (184 µs packet) | 45.2 |
| Decoded complete / truncated owned | 30 / 0 |
| Expected complete but not decoded | 15.2 |
| Events with no window overlap (acquisition misses) | 48,385 |

Acquisition, not decoding, dominates the miss count: only about 0.13% of
counted events overlap a captured window at all.

## The two corrections

1. **Carrier offset.** Access-address carrier estimates show this board's
   ch37 signal about 0.8 MHz above nominal, the same residual the
   [first owned decodes](../ble-owned-decoding/README.md) recorded (+0.83 MHz).
   Shifting by −1.8 MHz instead of −1 MHz moves the residual to tens of kHz.
   The estimate comes from access-address correlation, not from owned matches.
2. **Header bit 5.** This host's controller sets the ChSel-position bit on
   ADV_EXT_IND. The v1 profile rejects that bit as reserved. The explicit
   `--accept-chsel` option relaxes only that bit; bits 4 and 7 are still
   rejected, and the default is unchanged.

The legacy decoder with the −1.8 MHz shift also recovered 3 CRC-valid foreign
legacy packets (0 at −1 MHz).

## Limits

The denominator is controller-completed events, not independently observed
air emissions. The expected count assumes uniform event phase relative to the
windows. Power is uncalibrated, and there is one placement and one controller.
The receiver image was left installed for the [live console](../../../tools/live_console.py)
session, so **restoration of the original image is still pending**.

Machine-readable summary: [results.json](results.json). Raw IQ, the private
AdvA reference, full source logs and the flash read stay under ignored `.scratch/`.
