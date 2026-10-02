## Context

See [proposal](proposal.md) for the problem and scope. The hardware identity is recorded separately from untested reception and transport behavior.

## Goals / Non-Goals

**Goals:** A measured go/no-go decision for a useful FPGA transport or processing role, not a predetermined continuous SDR.

**Non-Goals:** No promise of 80 MS/s streaming on LX6; no blind reuse of S3 dedicated GPIO/SIMD; no arbitrary transmitter.

## Decisions

The original chip lacks the S3-specific fast lane used by eSpDR. Benchmark SPI/I2S or decimated/FFT output on LX6 first. An FPGA can buffer or process data only after the ESP exposes it. Keep an S3-plus-FPGA design as a separate outcome if the original chip is the bottleneck.

The host records revisions/settings/results; firmware owns modem and memory access; an FPGA, if selected, owns only its explicitly measured transport/processing boundary.

## Concrete FPGA candidates

Forgix is a small Trion T8F49 + RP2354 design with USB 1.1, not the DDR/FT600 USB 3 route in eSpDR. Start with bounded counters, FIFOs, triggering or decimation over verified SPI pins. Its PSRAM belongs to the board architecture; do not assume it is directly usable as a high-rate FPGA sample buffer.

The host PCIe device dabc:1017 is associated with AS02MC04/XCKU3P in prior local notes. Treat that as an identification candidate. Confirm markings and a reversible JTAG/PCIe bring-up path before any programming or DMA benchmark. Record available FPGA memory independently of PCI BAR sizes.

[Inventory and provenance](docs/evidence/fpga-inventory/README.md), [Adiuvo design](https://forgix.tech/) and [primary LiteX example](https://github.com/enjoy-digital/aduivo_forgix_test).

## Risks / Trade-offs

SRAM ownership/capture gaps may remain even with faster output. Electrical compatibility, clocks and available GPIO are unknown until inventory. Two hundred MB/s is payload, not bus line rate.

## Validation and decision

An inventory plus sustained payload, loss/backlog and timing measurements. 80 MS/s × 20 bits requires 200 MB/s before framing; lower-rate or spectral output alternatives get separate budgets.

Inventory is the first proof artifact. The benchmark command is selected only after its hardware interface exists; acceptance requires timestamped sequence/CRC counters and a measured sustained rate, not peak link marketing. RF integration is conditional on measured synthetic feasibility.

## Visual plan

[Experiment flow and provenance](docs/design/the-fpga-route-has-a-measured-feasibility-decision/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.

## Implementation findings

[The feasibility checkpoint](docs/evidence/fpga-inventory/README.md) separates current USB/PCI observations, pinned primary design review, and generated capacity calculations. It identifies a bounded completed-snapshot SPI path; direct RF SRAM DMA and continuous acquisition are not established. Forgix USB cannot sustain the raw 80 MS/s stream; a filtered lower-rate or event/spectrum path still needs a real benchmark. Physical board grade/clock mismatches against LiteX and an unavailable verified FPGA host transport keep later gates open.

The [local toolchain setup](docs/research/forgix-toolchain.md) now provides
Task commands for completed-download discovery, private permanent staging,
versioned Linux installation and execution through the locked Nix FHS runtime.
Thirty-three offline tests pass. [Actual installation evidence](docs/evidence/efinity-install-001/README.md)
now verifies Efinity 2026.1.132 installation, repeat reuse, real vendor CLI and
full host/vendor checks inside Nix FHS after a retained Python-environment
failure was corrected. No licensed compile has been verified. This setup
closes no physical inventory or transport benchmark task.
