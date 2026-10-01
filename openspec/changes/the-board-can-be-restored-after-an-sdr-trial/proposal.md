## Why

An SDR installation replaces the current firmware. We need a complete, identifiable fallback before experimenting with the only confirmed board.

## What Changes

- Preserve the whole 4 MiB flash privately, with size and SHA-256 recorded publicly.
- Record partitions, security state and a baseline boot; prepare a bounded recovery procedure.
- Prove restoration after the first SDR trial with a fresh boot matching the baseline.

## Capabilities

### New Capabilities

- `board/firmware-preservation`: A recovery route that restores the observed GPIO test, or a separately selected AtomVM image, with clearly distinct provenance.

### Modified Capabilities

None. Existing identity records remain factual baselines.

## Impact

Physical ESP32 and host UART. No FPGA or RF source required.

Dependencies: None; this is the first physical experiment.

## Non-goals

No flash dumps on the site; no assumption that the current image is AtomVM; no unrequested radio transmission.

## Decision gate

A 4,194,304-byte backup with SHA-256 plus a recorded restoration boot; a backup alone does not close recovery proof.

## Evidence and sources

Baseline: [board-identification](docs/evidence/board-identification/README.md). Sources: [primary-source register](docs/research/source-index.md).
