# Controlled spectrum session 001: channel location not confirmed, clipping mapped

Recorded 2026-10-06 under the [pre-declared protocol](../../research/spectrum-controlled-001-protocol.md).
The original image was preserved before the session, and restored and verified
by full readback afterwards.

## A. Source-on/off pairs (task 1.2): not confirmed

Each of BLE channels 37, 38 and 39 got three pairs of 40 s OFF and 10 counted
cycles ON: 30/30 cycles and 7,650 events per channel, all `0x43/255`. Only 1
of 9 pairs put its ON-minus-OFF excess peak within 2 MHz of the expected
+1.8 MHz. The other peaks scattered from −7.9 to +6.9 MHz, and every pair
showed 8–14 dB of excess (8 dB on ch39). No owned packet decoded in any pair.

The method failed, not necessarily the receiver. The burst-gated spectrum takes
the strongest 64 µs block of each window. Our source occupies only about 1% of
the time, so ambient 2.4 GHz bursts dominate both ON and OFF averages. The
zero decodes are unexplained: the part B rate predicts about 6 on ch37.
Channel location remains established only for ch37, by decoded owned packets in
the [hit-rate runs](../ble-receiver-hitrate-002/README.md).

## B. Filter and gain sweep on the fixed ch37 source (task 2.1): partial

| Condition | Mean AC power | Endpoint fraction mean / max | Owned decodes |
| --- | ---: | --- | ---: |
| BW 12, AGC | 468 | 0.06% / 0.8% | 1 |
| BW 20, AGC | 703 | 0.11% / 1.3% | 1 |
| BW 40, AGC | 1,384 | 0.43% / 7.9% | 2 |
| BW 67, AGC | 1,311 | 0.28% / 2.0% | 1 |
| BW 20, gain 16 | 6 | 0 / 0 | 0 |
| BW 20, gain 32 | 153 | 0.01% / 0.4% | 0 |
| BW 20, gain 48 | 2,882 | 1.6% / 14% | 0 |
| BW 20, gain 64 (41 windows) | 2,943 | 2.2% / 20% | 1 |

Hardware AGC keeps clipping low across every filter setting. Manual gain 48
and above clips heavily in some windows, and gain 16 leaves almost no signal.
Bandwidths above 16 MHz can't be distinguished at the 16 MS/s capture rate.
Decodes are too few to rank sensitivity. The gated peak is dominated by
ambient bursts, so it gives no centre offset.

The gain-64 capture failed after 41 windows on a short UART payload, which is
retained privately. Gain 72 and part C did not run (stop condition).

## C. Extended tuning (task 2.2): not run

## Limits

Levels are uncalibrated ADC codes. Part A's statistic is not specific to the
owned source at its duty cycle. Summary: [results.json](results.json); raw IQ
and logs stay under ignored `.scratch/`.
