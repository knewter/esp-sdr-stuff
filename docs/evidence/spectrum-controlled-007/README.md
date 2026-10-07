# Controlled spectrum session 007: ch39 not received by the CYD

Recorded 2026-10-07 under the
[pre-declared protocol](../../research/spectrum-controlled-007-protocol.md)
(`f564002`). The receiver is the [Cheap Yellow Display](../cyd-waterfall/README.md)
at 16 MS/s with BW 12. The counted source ran on ch39 (30 cycles per capture).

**Declared result: no owned ch39 packet at any LO.** Captures at LO 2443,
2455, 2467, 2479, 2491, 2503 and 2515 MHz (600 windows each, decoded over
−7.4 to +7.0 MHz) cover about 2436–2522 MHz. If the board received the
source, each LO expected about 18 complete packets. The decoder was working:
it logged header rejects and truncated packets at every LO. As declared, the
ch39 pairs were not run.

**Exploratory cross-checks (not part of the protocol).** With ch39 requested,
one 390-window capture at the board's ch37 settings (LO 2401) and one at its
ch38 settings (LO 2425) each decoded **0** owned packets over 20 counted
cycles. When the source was requested on those channels, each pair had 5–11.
So the source does leave ch37 and ch38 and is presumably on ch39. This board
does not decode it anywhere within about ±44 MHz of 2480 MHz.

**Task 1.2 stays open.** ch37 and ch38 are confirmed
([session 005](../spectrum-controlled-005/README.md)); ch39 is not received.
Separating a receiver-side cause from the source's real output at 2480 MHz
needs an independent 2.4 GHz receiver, such as a production ESP32-C5/S3 or a
different SDR. Summary: [results.json](results.json).
