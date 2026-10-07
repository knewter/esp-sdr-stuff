# Controlled spectrum session 006: 40 MS/s ch39 search, inconclusive

Recorded 2026-10-07 under the
[pre-declared protocol](../../research/spectrum-controlled-006-protocol.md)
(`31a9ac7`). The receiver is the [Cheap Yellow Display](../cyd-waterfall/README.md)
at 40 MS/s with BW 40. The counted source ran on ch39.

**Declared result.** Search captures at LO 2460, 2480 and 2500 MHz, decoded
over ±19.2 MHz, found **no owned packet**. As declared, the ch39 pairs were not
run, and ch39 stays unlocated. Each capture's decoder output held only 4–6
header rejects.

**Exploratory positive control (not part of the protocol).** One 200-window
capture at LO 2401 MHz and 40 MS/s, with the source on ch37. It decoded owned
packets in ON windows (2 after de-duplication, 0 OFF), at 2404.19 MHz as in
sessions 004 and 005. The 40 MS/s decode path works.

**Why the negative is weak.** A 409.5 µs window holds a whole 184 µs packet
only about 0.9 % of the time. Each 200-window capture therefore expected about
1.6 packets even with ch39 in view, so seeing none had about a 20 % chance.
Session 005's 16 MS/s search, with about 6 expected per capture over roughly
2464–2496 MHz, remains the stronger negative.

**Next.** [Session 007](../../research/spectrum-controlled-007-protocol.md)
searches at 16 MS/s with enough windows to expect about 18 packets per LO,
over about 2435–2523 MHz. Summary: [results.json](results.json).
