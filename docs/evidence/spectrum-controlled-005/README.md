# Controlled spectrum session 005: ch37 and ch38 confirmed, ch39 unlocated

Recorded 2026-10-06 under the
[pre-declared protocol](../../research/spectrum-controlled-005-protocol.md)
(`59c6122`; the search-grid endpoint wording was corrected in `d65ca47`
before any data existed). The receiver is the
[Cheap Yellow Display](../cyd-receiver/README.md) at 16 MS/s with BW 12.
Each channel had its own LO and grid, informed by
[session 004](../spectrum-controlled-004/README.md).

Every capture completed. UART fault recovery lost a few windows per capture
under heavy host load, and no capture aborted.

| Channel | LO | Pair 1 | Pair 2 | Pair 3 | Owned OFF | Carrier vs nominal | Confirmed |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 37 | 2401 MHz | 7 | 5 | 8 | 0 | +2.26 to +2.32 MHz | **yes** |
| 38 | 2425 MHz | 6 | 11 | 8 | 0 | −6.88 to −6.91 MHz | **yes** |
| 39 | — | — | — | — | — | not found | no |

Each pair column counts owned packets decoded in ON windows.

- **ch38 is now confirmed under a pre-declared protocol.** This repeats the
  session 004 exploratory finding: its carrier sits about 6.9 MHz below
  nominal, within ±30 kHz across pairs.
- **ch37 has now confirmed twice on this board.** Its offset is +2.26 to
  +2.32 MHz here, against +2.40 to +2.59 MHz in session 004.
- **The ch39 search found no owned packet** at LO 2471, 2479 or 2487 MHz over
  translations from −7.4 to +7.0 MHz, about ±16 MHz around 2480 MHz. As
  declared, the ch39 pairs were not run.

**Task 1.2 is not satisfied**: two of three channels are confirmed. ch39 could
lie outside the search window, the board may not hear it, or the source may
not reach it. None of these has been tested yet. Summary:
[results.json](results.json).
