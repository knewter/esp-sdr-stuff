# Forgix FPGA clock episodes: 32 MHz measured, full round trip completed

Recorded 2026-10-05. **Episode 005 configured the Forgix FPGA from RAM,
captured 16 clock periods, and returned a complete CRC-verified reply. The
board then returned to its factory firmware, and its original flash was
verified.** Every sample was 2,398 PIO decrements, the same in episodes 002,
004 and 005. The implied FPGA oscillator is **31.92–32.13 MHz** at the RP's
nominal 150 MHz. That matches the 32 MHz marking but is not a calibrated
frequency.

## Admission

Every episode ran under the 2026-10-04 independently reviewed clock safety
scope, using the same FPGA bitstream (`00cd8abc…`).

| Registry entry | Commit | Firmware | Change |
| --- | --- | --- | --- |
| 1 | `2514834` | ARM003 | Reviewed candidate rebound to current inputs. Its five changed files were host-side only, an independent diff review found device behaviour unchanged, and the Nix closure differed only in `registrationTime`. |
| 2 | `54a79a9` | ARM004 | `dabdd78` drains TinyUSB's 256-byte transmit buffer before reboot. Reviewed as safe. |
| 3 | `86a3dca` | ARM005 | `f2e5622` keeps the observer enumerated while the host holds the port, within the same drain deadline. |

Each firmware change touched `main.c` only and passed the startup audit with
the unchanged result class. All 94 offline clock tests pass. The main harness
now models the FIFO and fails on the pre-fix firmware.

## Episodes

| # | Result | What it showed |
| --- | --- | --- |
| 001 | Failed before ROM entry | Factory serial open timed out. User added a ModemManager ignore rule and replugged. |
| 002 | Failed: 256/512 reply bytes | First FPGA configuration and measurement. The firmware rebooted before its USB FIFO drained. |
| 003 | Failed before ROM entry | Factory USB control requests took ~5.1 s each. A power cycle cleared it; cause unknown. |
| 004 | Failed: post-reply identity check | Full reply with valid CRC, but the image rebooted before the host's final identity check. |
| **005** | **Completed (exit 0)** | All stages, a CRC-valid reply, factory return and full-flash verification. |

After every episode that entered the ROM, the original 2 MiB flash and factory
application were verified. No flash write occurred in any episode. The operator
retained and resolved each pending-finalization marker inside that episode's
private folder.

## Episode 005 reply

| Field | Value |
| --- | --- |
| Reply / CRC32 | 512 bytes / valid |
| FPGA configuration status / time | 0 / 2,827.297 ms (same in 002 and 004) |
| Observer status / samples | 0 / 16 in 1.224 ms |
| Every period sample | 2,398 decrements |
| Digital FPGA/PIO ratio | 256/1203 – 256/1195 |
| At nominal 150 MHz RP clock | 31.92–32.13 MHz |

## Independent review

An independent offline review of the saved episode 005 receipts **accepts** it
as one completed relative clock-ratio measurement with verified factory and
flash recovery. The review recomputed:

- the CRC, the nonce echo and the build/image hash fields;
- the timeline bounds, all within protocol limits;
- the ratio fractions;
- the post-run flash copies, which match the baseline.

It also confirmed identical samples in episodes 002 and 004.

## Limits

The RP clock is uncalibrated, and the digital bound excludes pad and
synchronizer effects. This proves the configured FPGA's clock reaches the RP
through the reviewed observer route. It does not prove SPI timing, register
readback or transport throughput. The FPGA speed grade still comes from the
schematic (T8F49I2X; LiteX says C2, the same speed grade). The episode 003
factory-USB stall is unexplained, and a power cycle cleared it.

Summary: [results.json](results.json). Session receipts, raw replies, marker
resolutions and flash images stay under ignored `backups/`.
