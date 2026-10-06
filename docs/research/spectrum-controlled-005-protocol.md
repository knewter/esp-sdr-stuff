# Controlled spectrum session 005: pre-declared protocol (task 1.2)

Declared 2026-10-06, before any session 005 data exists. It applies what
[session 004](../evidence/spectrum-controlled-004/README.md) found. On the
Cheap Yellow Display, the tuning error depends on the LO: ch37 lands
+2.4 to +2.6 MHz above nominal, while in exploration ch38 sat 6.8 MHz below
it. ch39 was not found within ±8 MHz.

## Unchanged from session 004

- **Receiver:** the CYD running `550fade-uart921600`, confirmed as an ESP32 by
  esptool before the run.
- **Captures:** BW 12, hardware gain, 16 MS/s, 8-bit, `--recover-faults 30`.
- **Source:** the counted source on the requested channel.
- **Analysis:** `--accept-chsel` and the owned reference. A packet counts once
  per window and access position within 4 µs. Guards are 100 ms. Each
  carrier is LO − translation + residual.
- **Per-channel confirmation:** three pairs, each with at least one owned
  packet in ON windows, and none in OFF windows in any pair.
- **Task 1.2** is satisfied only if all three channels confirm.

Each pair is one 390-window capture. The source starts 25 s in and runs 20
counted cycles.

## Per-channel settings

| Channel | LO | Translation grid |
| --- | --- | --- |
| 37 | 2401 MHz | −0.2 to −4.2 MHz, 0.4 MHz steps (as session 004) |
| 38 | 2425 MHz | +3.4 to +7.4 MHz, 0.4 MHz steps (centred on the 2419.2 MHz carrier) |
| 39 | chosen by the search below | ±2.0 MHz around the search result |

## ch39 search, then pairs

1. **Search captures.** One capture at each of LO 2471, 2479 and 2487 MHz:
   200 windows, with the source starting 10 s in and running 15 counted
   cycles on ch39.
2. **Search decode.** Each search capture is decoded over translations from
   −7.4 to +7.4 MHz in 0.8 MHz steps. Together the three captures cover
   carriers from about 16 MHz below to 16 MHz above 2480 MHz.
3. **Selection** (`tools/spectrum_session_analysis.py search`). Take the LO
   with the most owned ON packets; ties go to the LO nearest 2479. The pair
   grid is the median translation, rounded to 0.2 MHz, ±2.0 MHz in 0.4 MHz
   steps, kept inside ±7.6 MHz.
4. **Pairs.** Run the three ch39 pairs at the selected LO. Search captures
   count only for selection, never for confirmation.
5. **Nothing found.** If no search capture decodes an owned packet, the ch39
   pairs are not run, ch39 is reported as unlocated, and task 1.2 stays open.

## Stop conditions

On a capture abort (more than 30 faults, or any other error), keep the
completed captures and skip the rest. No retry. The board keeps the ESP-SDR
image.
