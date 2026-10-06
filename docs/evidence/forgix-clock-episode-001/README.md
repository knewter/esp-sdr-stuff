# First Forgix FPGA episode: configured and clocked, reply cut short

Recorded 2026-10-05. **The Forgix FPGA was configured from RAM for the first
time on this board, and the clock observer measured 16 identical periods.**
The implied FPGA oscillator is **31.92–32.13 MHz**, using the RP's nominal
150 MHz clock. The episode is still recorded as **failed**: the host received
only 256 of the 512 reply bytes, so the end-to-end CRC never arrived.

## Admission

Episodes ran under the 2026-10-04 independently reviewed clock safety
candidate, rebound to current inputs (commit `2514834`). Since that review,
five pinned files had changed host-side only:

- lease and finalization bookkeeping;
- the unrelated capture and Taskfile additions.

The Nix closure differed only in `registrationTime`. An independent diff review
found device behaviour unchanged, and all 94 offline clock tests pass.

## Episodes

| Episode | Result |
| --- | --- |
| 001 | Failed before ROM entry: opening the factory serial port timed out setting modem-control lines. No load or write happened. |
| Fix | User installed a udev rule so ModemManager ignores `2e8a` devices, then replugged. The operator retained and resolved the pending marker; the clock trial's recovery verified the original flash and factory application. |
| 002 | All stages ran: preserve, ROM, RAM load, observe, factory return, post-run preservation. Observation failed only on reply transport. The original flash and factory application were verified afterwards; no flash write occurred. |

## Episode 002 reply (first 256 bytes)

| Field | Value |
| --- | --- |
| Magic / nonce echo / build and image hash fields | `FGCR` / match / match |
| FPGA configuration status | 0 (2,827 ms) |
| Observer status / samples | 0 / 16 in 1.226 ms |
| Every period sample | 2,398 PIO decrements |
| Digital FPGA/PIO ratio | 256/1203 – 256/1195 (0.2128–0.2142) |
| At nominal 150 MHz RP clock | 31.92–32.13 MHz |

## Cause and next step

`firmware/forgix-clock-observer/main.c` reboots as soon as all 512 bytes are
handed to TinyUSB. Up to 256 bytes can still be in its transmit buffer, and
those are lost. The protocol already allows draining until `encoded + 2 s`. The
correction keeps servicing USB until the buffer empties, within that deadline.
It changes the ELF, so it needs a fresh build, an artifact audit, and a
qualification bound to the new image before a CRC-complete episode.

## Limits

The partial reply lacks the end-to-end CRC, although USB packets carry their own
CRC. The RP clock is uncalibrated. The digital bound excludes pad and
synchronizer effects. FPGA tasks 3.3 and 3.4 stay open.

Summary: [results.json](results.json). Session receipts, the raw reply, the
pending-marker resolution and flash images stay under ignored `backups/`.
