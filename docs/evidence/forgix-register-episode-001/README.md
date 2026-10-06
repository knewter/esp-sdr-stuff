# Forgix register readback: counter and scratch over SPI, FPGA at 32.000 MHz

Recorded 2026-10-06. **The Forgix RP configured the register FPGA image from RAM,
then completed a 13-command register session over the guarded on-board SPI
bus.** It wrote and read back three scratch patterns, read counter `0x1000`
twice, restored the scratch register and finished cleanly. The board then
returned to its factory application, and its original flash was verified.

| Check | Result |
| --- | --- |
| Scratch patterns `0x1357ACE0`, `0xA55A1122`, `0` | All read back exactly; the original value was restored and verified |
| Counter `0x1000` | 36,357,979 → 51,483,782 (delta 15,125,803) |
| Counter rate from host timestamps (whole-exchange brackets) | 30.28–34.11 MHz |
| Counter rate from bridge timestamps (472,684 µs) | **31.99982 MHz** (−5.6 ppm, relative to the nominal RP clock) |
| Responses | 13 of 13 with valid CRC, sequence, nonce, status 0 and build hash |
| Recovery | All stages completed; before and after flash reads equal the baseline; 0 writes |

The bridge-timed figure agrees with the independent
[clock-observer result](../forgix-clock-episode-001/README.md) (31.92–32.13 MHz).
Two different FPGA designs and measurement methods both put the oscillator at
32 MHz.

## Attempts

1. **Episode 001: the FPGA configured, then the ARM exchange timed out.** The
   host worker re-hashed every frozen input on each identity check, using up
   the 2 s per-exchange budget before it read the reply. Commit `8a70439` now
   runs that re-hash at most once a second; lease, lock and USB identity are
   still checked on every call. An independent review found it safe, and its
   regression test fails on the old code. Flash and factory state were
   verified afterwards.
2. **A rerun was refused before touching the device.** The pinned Pico SDK store
   path had been garbage-collected. It was rebuilt from the locked flake with an
   identical NAR hash, and the runtime closure is now GC-rooted under ignored
   `.scratch/`.
3. **Episode 002 completed** (exit 0).

## Admission

The registry entry binds:

- configuration artifact 007, the reviewed bridge firmware with the register
  candidate-003 FPGA image;
- the post-FINISH fix `57cae1c`, which no longer requires the bridge after a
  verified FINISH;
- the measured clock, and the speed-grade-2-only fact from Efinix.

An independent review found the register bitstream uses the same SPI guard and
pins as the synthetic image that already ran, with about 7.3 ns of timing slack.

## Independent review

An independent offline review of the saved receipts **accepts** FPGA task 3.4.
Two caveats:

- The original scratch value was 0, so by value alone the restore write looks
  the same as the last pattern. The non-zero patterns prove that writes take effect.
- The bridge-timed frequency relies on the uncalibrated RP crystal. The
  host-bracketed bounds do not.

## Limits

This shows functional SPI register access at about 0.97 MHz SCK and a counter
rate. It does not measure external pad timing, test SPI at higher clocks, or
connect any radio signal.

Summary: [results.json](results.json). Receipts and raw transcripts stay under
ignored `backups/`.
