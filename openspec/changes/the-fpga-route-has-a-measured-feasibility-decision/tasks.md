## 1. Select a compatible architecture

- [ ] 1.1 Record actual FPGA boards, memories, host links, logic voltages and clock options; verify against their primary manuals. Inventory Forgix revision/USB 1.1/SPI wiring separately from the PCIe candidate identification and bring-up status.
- [ ] 1.2 Read the original chip capture/peripheral paths and identify a bounded route; produce throughput and buffer budgets for raw, decimated and spectrum output.

## 2. Benchmark before RF integration

- [ ] 2.1 Run a synthetic sequence through the selected host transport at several rates; retain counters, CRC, sustained throughput, stall/backlog and signal-timing evidence.
- [ ] 2.2 If synthetic capacity and SRAM access pass, try a bounded RF integration and measure continuity; otherwise record the failing limit.
- [ ] 2.3 Publish a decision: original-chip improvement, separate S3 front end, or no useful FPGA route, with evidence supporting the choice.

## Proof procedure

Inventory is the first proof artifact. The benchmark command is selected only after its hardware interface exists; acceptance requires timestamped sequence/CRC counters and a measured sustained rate, not peak link marketing. RF integration is conditional on measured synthetic feasibility.

Required outcome: An inventory plus sustained payload, loss/backlog and timing measurements. 80 MS/s × 20 bits requires 200 MB/s before framing; lower-rate or spectral output alternatives get separate budgets.
