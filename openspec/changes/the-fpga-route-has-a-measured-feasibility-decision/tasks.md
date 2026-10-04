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

The [private register collector](docs/evidence/forgix-spi-collector/README.md)
now retains raw prefixes and transfer intents on disk, checks caller-supplied
lock/enumeration, and verifies transport closure. Fifteen own-operator tests
pass using compiled-C replies, injected failures and a local PTY. No physical
collector CLI or complete bounded load/recovery owner exists. No new hardware
trial ran; configuration transition and physical gates remain open, at 1/5.

The [offline lifecycle controller and bounded worker wrapper](docs/evidence/forgix-spi-lifecycle/README.md)
now pass 20 own-operator checks. Injected receipts test preservation/mutation
ordering, image/transition matching, failure retention and cleanup policy;
real regular-file/process fixtures verify inherited-lock and whole-group
closure. No physical backend, FPGA configuration writer or load/program CLI
is implemented. Tasks 1.1 and 2.1–2.3 remain unchecked. These software checkpoints
support task 2.1 without replacing its several-rate physical transport proof.

The [exact-image configuration variant](docs/evidence/forgix-spi-config/README.md)
now compiles after SDK startup and passes 15 own-operator configuration checks.
It allocates 202,680 SRAM bytes, includes the complete 173,380-byte decoded
candidate and passes the linked startup audit. Register-only bridge009 remains
27,968 bytes. The separate profile's 256 KiB guard preserves the original
128 KiB profiles. No device was opened or programmed. Physical grade/clock,
pin handoff, identity-selected backend and independent loading/recovery review
remain gates. Task 1.1 and tasks 2.1–2.3 stay unchecked, at 1/5.

The [identity-selected backend preparation](docs/evidence/forgix-spi-backend/README.md)
now passes 20 own-operator fault checks. It binds preserved USB identity,
configuration/source/ELF hashes, inherited-lock serial workers and separately
owned USB containers. Rebuilt configuration002 and register-only010 advertise
the SDK unique ID and allocate 203,152 and 28,440 SRAM bytes. Linked reset and
pre-main UID constructor inspections pass within their stated scope. The empty
qualification registry disables every hardware stage; no production coordinator
or independent backend review exists. No device was opened or FPGA programmed.
Physical UID continuity, grade/clock/pin timing, register readback and the
several-rate transport measurements remain outstanding. No checkbox changes.

## Production coordinator and checked UID follow-up

The [coordinator checkpoint](docs/evidence/forgix-spi-coordinator/README.md)
adds a production entrypoint behind the empty committed qualification registry,
complete frozen execution inputs and a durable pre-access session lease. The
qualification receipt covers executable inputs except the registry; the registry
is separately frozen from committed bytes to avoid a circular hash dependency.
One acceptance clock includes initial receipt writes. Failed initial preservation
also requires recovery because preservation enters ROM. The legacy standalone
physical preservation CLI is retired; its API remains inside guarded helpers.

New RAM configuration003/register011 initialize UID after watchdog enable,
check the ROM result and fail before USB on invalid identity. Actual builds
and reset audits pass within their offline scope. No physical episode is admitted:
the current survey finds no matching Forgix, and grade/clock/pin timing remain
unqualified. The nominal32MHz photo marking is separate from a measured clock.
The existing wiring gives the RP only oscillator enable, not oscillator output.
No hardware checkbox or accepted requirement changes.

## Finite selected-transport preparation

The [new finite synthetic protocol](docs/research/forgix-synthetic-transport-protocol.md)
requires a separately versioned FPGA FIFO/source and autonomous RP/host path.
The current 24-command register bridge cannot measure sustained streaming.
Start with 256/1,024/2,048 B/s offered rates at the current conservative PIO
preset; old 10/20/40 MHz wire suggestions exceed the existing guard and are
superseded for this route. Source HDL, actual C/host codecs, SRAM/artifact audits
and whole-path independent review are implementation prerequisites, not task
2.1 acceptance. Physical grade/clock/pins, matching attachment and preservation
remain gates. Several-rate sequence/CRC, backlog/loss and timing measurements
are still required; no checkbox or accepted requirement changes.


The [reviewed finite source](docs/evidence/forgix-synthetic-source/README.md)
now passes 34 peer-replayed tests and five actual-HDL probes, including generated
SPI integration. Root regenerates private RTL and runs source HDL in regular CI.
Separate source region preserves the old bank/guard; source-record rates remain
prospective, not measured stream throughput. Resource fit, RP/host stream,
physical qualification and complete recovery remain gates. Task 2.1 stays open.

## Reviewed implementation prerequisites

The [finite codecs](docs/evidence/forgix-synthetic-codec/README.md) pass actual native-C/Python and independent fault replay after a retained overlapping-output correction. The [compiler route](docs/evidence/forgix-synthetic-compiler/README.md) retains its first actual FHS failure before generation: committed-input verification requires Git, now explicitly supplied by Nix. Runtime verification, actual vendor compilation/report review, RP stream, physical qualification and complete recovery remain gates. No transport task is accepted.

## Actual routed failure and reviewed correction

The [actual compiler reports](docs/evidence/forgix-synthetic-compiler/README.md) fit the requested target resources but miss internal 32 MHz setup by 0.694 ns. Exact vendor XML rewrite and empty-auxiliary inventory corrections pass review. The [deadline-register optimization](docs/evidence/forgix-synthetic-timing/README.md) preserves cycle behavior in actual differential HDL tests. Fresh routed timing, RP/host stream, physical grade/clock/pins and complete recovery remain gates; no task is accepted.

## Third routed result and next scheduler proof

[Actual attempt003](docs/evidence/forgix-synthetic-compiler/README.md) passes
complete artifact/XML verification and independent report review but misses
internal 32 MHz setup by 1.763 ns. Requested-target resources fit; no physical
clock, pad timing or loading is qualified. The critical path is the 64-bit
relative scheduling comparison feeding finite completion. The earlier
deadline-register optimization preserves behavior but did not improve this
routed result.

Replace only the due scheduler with a period countdown. Preserve the exact
first/last record ticks, sequence/pattern/CRC, source offers under full FIFO,
START one-shot/window, concurrent POP/STOP/SNAPSHOT, coherent snapshots, reset
and five-second drain. Supported finite profiles last 60 nominal seconds; the
countdown must not change timestamps or silently throttle offers. Prove actual
old/new HDL equality with full-target profiles, carry/wrap and accelerated
reconciled edge states, then obtain independent review and a fresh vendor build
at unchanged 32 MHz. Continue RP/host and complete load/recovery review in
parallel. This closes no physical inventory or transport task.

The [finite RP core](docs/evidence/forgix-synthetic-stream-core/README.md) now passes
18 author and 11 independent actual-C/UBSan groups after three retained failed
peer episodes. Platform/ARM artifact, collector, physical qualification and
complete recovery remain prerequisites; no task acceptance follows.

The [countdown scheduler](docs/evidence/forgix-synthetic-scheduler/README.md) now
passes 16 author HDL groups and nine independent production-period edge fixtures
against immutable pre-change HDL. Fresh routed timing at unchanged 32 MHz remains
required; software behavior proof does not accept a physical task.
