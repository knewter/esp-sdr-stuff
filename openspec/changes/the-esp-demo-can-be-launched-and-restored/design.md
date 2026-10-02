## Context

The original ESP32 uses CP2102 UART rather than native USB. The accepted 512-bin session ran at 921,600 baud for 60 seconds; the first 1,024-bin session failed CRC. Existing tools verify artifact provenance, capture frame integrity and restoration writes separately. See [proposal](proposal.md) for motivation and [contract](specs/radio/interactive-demo/spec.md) for behavior.

## Goals / Non-Goals

**Goals:** Coordinate one exclusive hardware operator, a bounded physical capture, observable viewer state and verified baseline recovery through documented Task commands.

**Non-Goals:** Source calibration, counted BLE reliability, FPGA acceleration, continuous raw samples and AtomVM. These are separate evaluations with unchanged gates.

## Decisions

The host owns device identity, artifact validation, flashing, UART transport and cleanup. The pinned receiver owns snapshot acquisition and FFTs. The browser receives local HTTP data from the host and displays measured frames; it does not directly own the serial device. This preserves exclusive device access and reuses the tested protocol parser.

Use the previously successful 512-bin, nominal 80 MS/s, 2412 MHz requested center, 20 MHz requested filter and hardware-AGC profile as the initial demo default. Keep configurable settings explicit, and do not imply untested frequencies or settings work. The 1,024-bin failure remains historical evidence.

Verify the current full flash against the preserved baseline before installation. A differing image is retained privately and installation stops, avoiding replacement of newly installed user firmware. The standalone recovery action deliberately has no current-baseline equality prerequisite because it must recover a receiver or interrupted installation.

Bind an owned loopback server before installing; validate the browser start request for this session. A separate owned capture worker allows bounded termination and serial-handle closure before restoration. The default lifecycle restores after capture success, failure or cancellation. A worker that cannot be closed prevents competing restoration and produces explicit recovery failure.

The existing flash tool verifies source/configuration metadata, part hashes and bounds, preserved backup hash and security observations. Add an independent complete readback and matching boot observation after restoration; write verification alone is insufficient. Full dumps and raw logs use fresh private storage with restrictive permissions. Publish selected numerical outcomes and sanitized known boot proof only.

Headless proof uses Chromium from Nix to start the same viewer and retain live and completed screenshots. Those screenshots prove the displayed session; frame receipts and private payload replay prove acquisition integrity. Smooth rendering and synthesized sample indices remain distinct from RF continuity and calibrated timing.

## Risks / Trade-offs

- UART opening can reset the chip; use the existing bounded nonce-fenced synchronization.
- Full preflight and restoration readback add several minutes; retain those checks to establish the actual baseline and recovery.
- Host termination cannot remove power-loss risk; expose a standalone recovery task with the verified private image and retained failure receipts.
- The new Nix artifact has the pinned source and SDK but no claimed historical binary equivalence; identify the exact installed binary hashes and verify its fresh physical session.
- Snapshot gaps can hide brief signals; show gap flags and nominal coverage without claiming event hit rates.

## Migration Plan

Land the documented commands and failure tests, then execute a fresh physical session with the actual preserved board. Inspect and independently review frame data, screenshots and restoration before accepting the new requirements. Commit evidence before rendering the website and verify the deployed revision and exported sources. Preserve all prior failures and acceptance records.
