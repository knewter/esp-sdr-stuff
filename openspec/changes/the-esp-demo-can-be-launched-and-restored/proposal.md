## Why

The board has delivered verified radio snapshots and browser spectra, but repeating that demonstration requires several operator commands. A documented Task command should take the connected, preserved ESP32 through installation, an observable physical session and verified recovery.

## What Changes

- Add a Nix-backed demo task that verifies device identity, current baseline and receiver artifacts before installation.
- Serve a local spectrum viewer, record a bounded 60-second physical session and show reception gaps, explicit FFT averaging and uncalibrated power units.
- Restore the preserved original image after success, failure or cancellation, verify the full flash readback and observe the original application boot.
- Retain sanitized physical evidence and provide a separate recovery command for interrupted runs.

## Capabilities

### New Capabilities

- `radio/interactive-demo`: A repeatable physical spectrum demonstration with measured capture integrity and recovery.

### Modified Capabilities

None. Existing snapshot, recovery, RF characterization and counted-burst requirements retain their acceptance gates.

## Impact

Demo orchestration, the existing UART spectrum bridge, Taskfile, host failure tests and the evidence site. Requires the identified original ESP32, its two verified private baseline reads, a pinned receiver artifact, the Nix environment and exclusive device ownership. FPGA hardware and calibrated RF equipment are not dependencies for the first spectrum milestone.

Dependencies: [accepted snapshot capture](../archive/2026-10-01-the-board-captures-repeatable-radio-snapshots/proposal.md) and [accepted restoration](../archive/2026-10-01-the-board-can-be-restored-after-an-sdr-trial/proposal.md).

## Non-goals

No AtomVM, continuous raw I/Q, calibrated power, reliable burst-interception rate or FPGA transport claim. BLE reception and controlled RF measurements continue in their existing proposals.

## Decision gate

The documented Task command produces a fresh successful 60-second physical spectrum session with CRC/sequence/end-total checks and visible gap disclosure, then independently verifies all 4 MiB of the restored original flash and its matching application boot. Independent review must reproduce the integrity and recovery checks and inspect the live and completed viewer evidence. Failures remain recorded.

## Evidence and sources

[Prior physical spectrum session](docs/evidence/spectrum-baseline/README.md), [original-image preservation](docs/evidence/firmware-preservation/README.md), [measured limitations](docs/research/measured-recommendations.md), and [primary-source register](docs/research/source-index.md). These establish preparation and prior behavior; the new command still requires fresh physical proof.

## Retained trial checkpoint

The [first Task trial](docs/evidence/esp-demo-session-001/README.md) and second historical-artifact trial failed CRC; both independently restore the original full flash and boot. Executable firmware segments match, so these outcomes do not establish a build regression. The historical eight-window trial completed a minute. The fresh Nix-built repeat failed CRC after a receive stall, and both outcomes remain recorded. A host-storage intervention now buffers binary frames until UART closure; two consecutive Nix-built physical minutes completed with independent integrity and recovery review. Publication verification remains. This does not establish a corruption cause or general reliability rate.
