## Why

The user already has FPGA boards, but faster USB alone does not remove the original ESP32 capture-path limits. We need to establish where an FPGA can actually help before wiring a high-rate bus.

## What Changes

- Inventory FPGA model, RAM, host interface, spare pins and I/O voltage.
- Compare original-ESP32 SPI/I2S/buffering/FFT routes with the S3 eSpDR reference design.
- Measure a bounded synthetic transport first, then decide whether to use this chip, an S3 front end, or another receiver.

## Capabilities

### New Capabilities

- `transport/fpga-feasibility`: A measured go/no-go decision for a useful FPGA transport or processing role, not a predetermined continuous SDR.

### Modified Capabilities

None. Existing identity records remain factual baselines.

## Impact

The user reports Adiuvo Forgix ownership; official design uses Trion T8F49 and RP2354 USB 1.1. Host enumeration also finds a PCIe FPGA candidate, with exact model attributed to prior research and bring-up untested. See [inventory](docs/evidence/fpga-inventory/README.md). Verify revisions, pins, voltages and clocks before wiring.

Dependencies: [the board captures repeatable radio snapshots](../the-board-captures-repeatable-radio-snapshots/proposal.md)

## Non-goals

No promise of 80 MS/s streaming on LX6; no blind reuse of S3 dedicated GPIO/SIMD; no arbitrary transmitter.

## Decision gate

An inventory plus sustained payload, loss/backlog and timing measurements. 80 MS/s × 20 bits requires 200 MB/s before framing; lower-rate or spectral output alternatives get separate budgets.

## Evidence and sources

Baseline: [research](docs/research/source-index.md). Sources: [primary-source register](docs/research/source-index.md).
