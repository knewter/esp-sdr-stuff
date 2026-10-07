# Controlled spectrum session 006: pre-declared protocol (task 1.2, ch39)

Declared 2026-10-07, before any session 006 data exists.
[Session 005](../evidence/spectrum-controlled-005/README.md) confirmed ch37 and
ch38 on the Cheap Yellow Display. Its ch39 search at 16 MS/s (about ±16 MHz
around 2480 MHz) found no owned packet. Session 006 searches more widely using
the board's 40 MS/s rate: ±20 MHz per capture, with 409.5 µs windows that still
hold whole 184 µs packets.

## Setup

- **Receiver:** the CYD, running the [waterfall build](../evidence/cyd-waterfall/README.md),
  whose host protocol and captures match the `550fade` receiver. Confirmed as
  an ESP32 by esptool before the run.
- **Captures:** 40 MS/s, 8-bit, BW 40, hardware gain, `--recover-faults 30`.
- **Source:** the counted source on ch39.

The analysis rules of session 005 are unchanged: `--accept-chsel`, the owned
reference, 4 µs de-duplication, 100 ms guards, and carrier = LO −
translation + residual. The analysis tool now takes `--rate 40000000`, and
re-running it reproduces session 005's result exactly.

## ch39 search, then pairs

1. **Search captures.** One capture at each of LO 2460, 2480 and 2500 MHz:
   200 windows, with the source starting 10 s in and running 15 counted
   cycles.
2. **Search decode.** Each capture is decoded over translations from −19.2 to
   +19.2 MHz in 1.2 MHz steps (33 points). Together the captures cover about
   2441–2519 MHz.
3. **Selection.** Take the LO with the most owned ON packets; ties go to the
   LO nearest 2479. The pair grid is the median translation, rounded to
   0.2 MHz, ±2.0 MHz in 0.4 MHz steps, kept inside ±19.6 MHz.
4. **Pairs.** Three ch39 pairs at the selected LO, also at 40 MS/s and BW 40:
   390 windows each, with the source starting 25 s in and running 20 counted
   cycles.
5. **Nothing found.** If no search capture decodes an owned packet, the pairs
   are not run and ch39 is reported as unlocated.

## Decision

**ch39 confirmed:** all 3 pairs decode at least one owned ON packet, and no
pair decodes one in OFF windows. **Task 1.2 is satisfied** if ch39 confirms
here, together with session 005's pre-declared ch37 and ch38 confirmations on
the same board. That makes three repeated source-on/source-off pairs at each
of the three advertising channels. Otherwise the task stays open.

## Stop conditions

On a capture abort, keep the completed captures and skip the rest. No retry.
