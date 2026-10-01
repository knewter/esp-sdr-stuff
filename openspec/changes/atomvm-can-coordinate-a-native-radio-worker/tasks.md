## 1. Define runtime boundaries

- [ ] 1.1 Pin the intended AtomVM release/configuration and account for the actual board resources; verify its build independently.
- [ ] 1.2 Inspect the native extension/port mechanism and draw ownership/lifetime boundaries plus an SRAM budget; verify no heap uses capture SRAM.

## 2. Measure a bounded prototype

- [ ] 2.1 Implement a short native capture/control prototype only after preservation; retain build revisions and a fresh boot confirming the runtime.
- [ ] 2.2 Run 100 capture/control cycles with CRC and VM latency/error counters; save results and compare with standalone SDR.
- [ ] 2.3 Decide single-chip integration, separate controller or defer, with explicit memory/timing evidence.

## Proof procedure

Host proof: pinned AtomVM build and linker-map budget. Board proof: timestamped 100-cycle capture/control run with CRC, heap/stack and latency counters. The future harness command belongs with the selected native port implementation.

Required outcome: A documented SRAM/linker budget and a bounded prototype that preserves CRC capture integrity and records VM latency over 100 capture/control cycles.
