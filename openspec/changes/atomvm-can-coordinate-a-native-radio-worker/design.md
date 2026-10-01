## Context

See [proposal](proposal.md) for the problem and scope. The hardware identity is recorded separately from untested reception and transport behavior.

## Goals / Non-Goals

**Goals:** A reasoned decision about AtomVM control of capture, not high-rate sample handling in Erlang.

**Non-Goals:** No ready-made AtomVM SDR API claim, simultaneous unrestricted Wi-Fi operation or bulk I/Q through ordinary processes.

## Decisions

Native code owns the modem registers, reserved SRAM and packing; AtomVM owns commands/status. Prefer a port/worker with bounded messages to a long blocking NIF. The alternative is an external AtomVM controller around dedicated SDR firmware.

The host records revisions/settings/results; firmware owns modem and memory access; an FPGA, if selected, owns only its explicitly measured transport/processing boundary.

## Risks / Trade-offs

The reserved 64 KiB and internal timing constraints compete with VM heap/task needs. Current AtomVM provenance is unknown. Wi-Fi radio resources are shared.

## Validation and decision

A documented SRAM/linker budget and a bounded prototype that preserves CRC capture integrity and records VM latency over 100 capture/control cycles.

Host proof: pinned AtomVM build and linker-map budget. Board proof: timestamped 100-cycle capture/control run with CRC, heap/stack and latency counters. The future harness command belongs with the selected native port implementation.

## Visual plan

[Experiment flow and provenance](docs/design/atomvm-can-coordinate-a-native-radio-worker/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.
