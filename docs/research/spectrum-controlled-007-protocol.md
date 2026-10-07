# Controlled spectrum session 007: pre-declared protocol (task 1.2, ch39)

Declared 2026-10-07, after [session 006](../evidence/spectrum-controlled-006/README.md)
and before any session 007 data exists.

Session 006's 40 MS/s search was underpowered: about 1.6 packets were
expected per capture, even with ch39 in view. Session 007 searches at 16 MS/s,
where a 1023.75 µs window holds a whole packet about 3.4 % of the time, so 600
windows per LO expect about 18 packets if ch39 is in view.

## Setup

- **Receiver:** the CYD waterfall build, confirmed as an ESP32 by esptool before
  the run.
- **Captures:** 16 MS/s, 8-bit, BW 12, hardware gain, `--recover-faults 30`.
- **Source:** the counted source on ch39.
- **Analysis:** as in sessions 005 and 006.

## ch39 search, then pairs

1. **Search captures.** One capture at each of LO 2443, 2455, 2467, 2479,
   2491, 2503 and 2515 MHz: 600 windows, with the source starting 10 s in and
   running 30 counted cycles.
2. **Search decode.** Translations from −7.4 to +7.0 MHz in 0.8 MHz steps
   (19 points). Consecutive LOs overlap, so the search covers about
   2436–2522 MHz.
3. **Selection.** Take the LO with the most owned ON packets; ties go to the
   LO nearest 2479. The pair grid is the median translation, rounded to
   0.2 MHz, ±2.0 MHz in 0.4 MHz steps, kept inside ±7.6 MHz.
4. **Pairs.** Three pairs at the selected LO: 390 windows each, with the source
   starting 25 s in and running 20 counted cycles.
5. **Nothing found.** If no LO decodes an owned packet, ch39 is reported as
   not received over 2436–2522 MHz at this sensitivity (about 18 expected
   packets per LO), and the pairs are not run.

## Decision

As in session 006. **ch39 confirmed:** all 3 pairs decode at least one owned
ON packet, and no pair decodes one in OFF windows. **Task 1.2 is satisfied**
if ch39 confirms here, together with session 005's ch37 and ch38 on the same
board.

## Stop conditions

On a capture abort, keep the completed captures and skip the rest. No retry.
