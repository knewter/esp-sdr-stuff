# Controlled spectrum session 004: ch37 confirmed on the CYD

Recorded 2026-10-06 under the
[pre-declared protocol](../../research/spectrum-controlled-004-protocol.md)
(`b94da4f`). The receiver is the [Cheap Yellow Display](../cyd-receiver/README.md):
an ESP32 rev v3.1 running the original receiver image, at 16 MS/s with BW 12,
over its CH340 at 921600. The controller-counted source ran 20 cycles per
pair. The adapter's position relative to the board was unknown.

All nine captures completed. Fault recovery lost 2–8 of 390 windows per
capture, with the host's load average at about 140. The first analysis pass
aborted on retained fault fragments. The fixed tool (`70d068f`) decodes only
complete windows, as session 003 did, with the grid and thresholds unchanged.

## Pre-declared result

| Channel | Pair 1 | Pair 2 | Pair 3 | Owned OFF | Carrier vs nominal | Confirmed |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| 37 | 3 | 5 | 7 | 0 | +2.40 to +2.59 MHz | **yes** |
| 38 | 0 | 0 | 0 | 0 | — | no |
| 39 | 0 | 0 | 0 | 0 | — | no |

Each pair column counts owned packets decoded in ON windows.

**ch37 is confirmed for the first time** (session 003 managed 2 of 3 pairs).
**Task 1.2 is not satisfied**, because ch38 and ch39 decoded nothing on the
declared grid (carriers from 0.8 MHz below to 3.2 MHz above nominal).

## Exploration after the result (not part of the protocol)

- **The source honours the channel map.** In one capture tuned to ch37 with
  the source requested on ch38, no owned packets decoded. With the source on
  ch37, each pair had 3–7.
- **ch38 sits 6.8 MHz below nominal.** Above nominal, decodes up to +6.8 MHz
  found nothing. Below nominal, **all three pairs decoded owned packets in ON
  windows (5, 7, 5) and none in OFF windows.** The carriers held at 2419.19 to
  2419.22 MHz, an offset of −6.78 to −6.81 MHz.
- **That is not an IQ image**, which would sit near 2424 MHz. The board's
  tuning error depends strongly on the LO: +2.5 MHz at LO 2401, against
  −5.8 MHz around LO 2425.
- **ch39 shows nothing** from 8 MHz below to 6.8 MHz above nominal. Its
  carrier may lie outside the ±8 MHz visible at 16 MS/s.
- **80 MS/s wideband captures** showed narrowband bursts across 2393–2439 MHz
  whichever channel the source used. They are too busy to locate the source by
  energy alone.

**Next:** pre-declare a session with ch38's grid around −6.8 MHz, and search
ch39 with shifted LOs or 40 MS/s windows, before claiming task 1.2. Summary:
[results.json](results.json).
