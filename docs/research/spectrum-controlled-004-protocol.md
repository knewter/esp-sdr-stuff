# Controlled spectrum session 004: pre-declared protocol (task 1.2)

Declared 2026-10-06, before any session 004 data exists. It repeats the
[session 003 protocol](spectrum-controlled-003-protocol.md) on a different
receiver board. Only the changes below differ from session 003.

## Changes from session 003

- **Receiver:** the [Cheap Yellow Display](../evidence/cyd-receiver/README.md),
  an ESP32-D0WD-V3 rev v3.1 running the same `550fade-uart921600` image. It is
  already installed and its original image is preserved, so this session does
  no install or restore. Its port is the CH340 at
  `usb-1a86_USB_Serial-if00-port0`, confirmed as an ESP32 by esptool before
  the run.
- **Fault recovery:** each capture runs with `--recover-faults 30`, the
  capture tool's opt-in mode added for the [C3 sessions](c3-burst-002-protocol.md).
  A faulted window is lost and reported. More than 30 faults in one capture
  aborts it.
- **Wider decode grid:** this board's tuning offset is unknown. The
  translation grid runs from −0.2 to −4.2 MHz in 0.4 MHz steps (11 points),
  covering carriers from 0.8 MHz below to 3.2 MHz above each channel centre.
- **Placement:** the source adapter's position relative to the board is
  unknown and is not controlled.

## Unchanged

- **Captures:** ch37/38/39 with LO 1 MHz below centre (2401, 2425,
  2479 MHz); BW 12, hardware gain, 16 MS/s, 8-bit; 390 windows per capture.
- **Pairs and source:** three pairs per channel. The source starts 25 s after
  each capture, running 20 counted cycles on that channel.
- **Analysis:** `--accept-chsel` and the owned reference. A packet counts once
  per window and access position within 4 µs. Guards are 100 ms. Each
  packet's carrier is LO − translation + residual.
- **Per-channel confirmation:** all 3 pairs decode at least one owned packet
  in ON windows and none in OFF windows. **Task 1.2 is satisfied only if all
  three channels confirm.** Otherwise the result is reported as is.

## Stop conditions

On a capture abort, keep the completed captures and skip the rest. No retry.
The board keeps the ESP-SDR image.
