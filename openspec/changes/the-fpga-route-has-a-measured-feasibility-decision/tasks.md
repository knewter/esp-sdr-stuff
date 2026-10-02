## 1. Select a compatible architecture

- [ ] 1.1 Record actual FPGA boards, memories, host links, logic voltages and clock options; verify against their primary manuals. Inventory Forgix revision/USB 1.1/SPI wiring separately from the PCIe candidate identification and bring-up status.
- [x] 1.2 Read the original chip capture/peripheral paths and identify a bounded route; produce throughput and buffer budgets for raw, decimated and spectrum output.

## 2. Benchmark before RF integration

- [ ] 2.1 Run a synthetic sequence through the selected host transport at several rates; retain counters, CRC, sustained throughput, stall/backlog and signal-timing evidence.
- [ ] 2.2 If synthetic capacity and SRAM access pass, try a bounded RF integration and measure continuity; otherwise record the failing limit.
- [ ] 2.3 Publish a decision: original-chip improvement, separate S3 front end, or no useful FPGA route, with evidence supporting the choice.

## Proof procedure

Inventory is the first proof artifact. The benchmark command is selected only after its hardware interface exists; acceptance requires timestamped sequence/CRC counters and a measured sustained rate, not peak link marketing. RF integration is conditional on measured synthetic feasibility.

Required outcome: An inventory plus sustained payload, loss/backlog and timing measurements. 80 MS/s × 20 bits requires 200 MB/s before framing; lower-rate or spectral output alternatives get separate budgets.

## Implementation checkpoint

Task 1.2 is grounded in [the pinned source review and reproducible budgets](docs/evidence/fpga-inventory/README.md). The bounded snapshot SPI route is selected for evaluation; DMA/SRAM reachability and sustained transport remain unverified.

Task 1.1 remains open because physical Forgix revision/clock and PCI card electrical interfaces are not verified. Tasks 2.1–2.3 remain open: no connected FPGA transport has been selected or measured, and the published decision is partial. [Host survey](docs/evidence/fpga-inventory/host-survey.json) identifies the current blockers and [inventory report](docs/evidence/fpga-inventory/README.md) lists concrete physical inputs.

[Physical MCU preservation](docs/evidence/forgix-preservation/README.md) now
verifies Forgix factory USB identity, software ROM entry, two identical reads
of the detected 2 MiB flash range, separate verification and original-application
return. It closes no FPGA task: PCB revision, clock and header wiring remain
uninspected; no FPGA sequence/CRC, sustained transport or RF integration ran.

A [complete generic vendor compiler test](docs/evidence/efinity-compile-smoke-002/README.md)
now passes through Nix and produces a fresh T8F81/C2 example image. The
[initial incomplete run](docs/evidence/efinity-compile-smoke-001/README.md) remains
failed; adding demonstrated SQLite and D-Bus runtime dependencies fixes the
Interface Designer import. This supports toolchain readiness only. The connected
Forgix needs its own confirmed T8F49 grade, clock, revision and wiring before
a guarded board build; task checkboxes remain unchanged.
