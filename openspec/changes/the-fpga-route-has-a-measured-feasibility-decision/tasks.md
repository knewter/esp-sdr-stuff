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

The separate [RAM-only synthetic USB preparation](docs/research/forgix-usb-ram-feasibility.md)
can narrow the downstream host-link budget without assuming FPGA constraints.
Actual compiled ELF, bounded lifecycle/recovery review and physical preflight
are still required; USB-only success would not complete task 2.1 for the selected
FPGA transport or establish SRAM/RF integration.

The [October 3 MCU USB follow-up](docs/evidence/forgix-usb-ram-recovery/README.md) retains failed005, verified recovery005 and condition006: 256 KiB/s loses 431 records, exactly accounted by device discards; full original-flash/factory preservation passes. Earlier 64 KiB/s remains qualified. This narrows the MCU segment, not the selected FPGA transport; checkboxes remain unchanged.

The [October 3 photo/BOM review](docs/evidence/fpga-inventory/README.md) resolves
the documented RP 12 MHz crystal and FPGA 32 MHz oscillator, but physical grade,
clock and revision remain unverified. A [provisional T8F49/I2 candidate](docs/evidence/forgix-toolchain/README.md)
now passes all four offline Efinity stages with exactly four assigned internal
pins. This is software preparation. The factory loader still drives MOSI after
END; reviewed RP SPI turnaround and a fresh preserved attachment precede any
physical readback. No FPGA transport/RF task closes; progress remains 1/5.

The [reconnect follow-up](docs/evidence/forgix-toolchain/README.md) now verifies
fresh original-flash copies, separate device comparison and factory return
after a retained serial-control failure and user reconnect. Guarded candidate003
passes offline compilation and asynchronous simulations. Its actual RP pin
release, grade/clock and register transport remain unqualified; no checkbox changes.

The [RAM PIO register bridge](docs/evidence/forgix-spi-bridge/README.md) now
compiles and passes C/PIO/guard host tests. Corrected bridge006 passes independent
offline artifact review and 11 actual-C deadline regressions; bridge004's failure
is retained. Linked PIO words match the tested words. This is offline preparation: physical parameters, independent startup
and load/recovery review, register readback and continuity remain gates.
No bridge was loaded or FPGA programmed; progress remains 1/5.

Bridge008 adds a tested finite host restoration engine and saved-ELF/SDK reset
audit. GPIO/pads/PIO reset before main, so prior FPGA image continuity needs
qualification or configuration after RAM startup. Host tests use injected
transport; no physical register trial ran. Complete identity-selected USB
load/recovery and physical timing remain open; progress stays 1/5.
