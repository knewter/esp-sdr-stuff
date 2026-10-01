> **Deferred by user, October 1, 2026.** Excluded from the active evaluation goal. Tasks remain open; no runtime integration is being attempted.

## Why

The intended board runtime was AtomVM, but the current firmware is a GPIO test and ESP-SDR is standalone. We need to determine whether runtime orchestration can coexist with native radio capture.

## What Changes

- Select and pin an AtomVM baseline independently of the current firmware.
- Prototype a native bounded capture worker with an Erlang control/result boundary.
- Measure memory, scheduling responsiveness and snapshot integrity, then decide whether a second controller is preferable.

## Capabilities

### New Capabilities

- `runtime/atomvm-radio`: A reasoned decision about AtomVM control of capture, not high-rate sample handling in Erlang.

### Modified Capabilities

None. Existing identity records remain factual baselines.

## Impact

Physical original ESP32 after preservation, native toolchain, and optional second MCU if single-chip memory/scheduling fails.

Dependencies: [the board can be restored after an sdr trial](../the-board-can-be-restored-after-an-sdr-trial/proposal.md), [the board captures repeatable radio snapshots](../the-board-captures-repeatable-radio-snapshots/proposal.md)

## Non-goals

No ready-made AtomVM SDR API claim, simultaneous unrestricted Wi-Fi operation or bulk I/Q through ordinary processes.

## Decision gate

A documented SRAM/linker budget and a bounded prototype that preserves CRC capture integrity and records VM latency over 100 capture/control cycles.

## Evidence and sources

Baseline: [board-identification](docs/evidence/board-identification/README.md). Sources: [primary-source register](docs/research/source-index.md).
