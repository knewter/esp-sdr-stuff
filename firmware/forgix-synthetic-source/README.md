# Finite synthetic FPGA source v1 — prospective preparation

This separately versioned source supports FPGA proposal task2.1 preparation.
It is not a physical FPGA/RP/USB benchmark. No RP stream firmware or host stream
collector exists here. Existing candidate/bridge/register ABI,24-command limit,
configuration and qualification registry remain unchanged. No load is admitted.

The new RTL-only wrapper reuses the original counter/scratch bank at1000/1004
and `GuardedSPIBone` unchanged, then adds a distinct4KiB Wishbone slave at10000.
It requests the same four onboard pins and nominal32MHz system clock. Efinity
resource fit, timing closure, clock/grade/pin qualification, matching SRAM-only
RP image and recovery are prerequisites, not generator results. No ESP input,
new interboard wires, PSRAM, DMA, continuous capture or RF integration is assumed.
The separate region avoids reallocating the old AutoCSR bank or changing its
addresses. The wrapper supplies an initialized one-cycle source reset, followed
by the existing system reset; device-specific uninitialized state is not assumed.

## Finite source and record

One START intent is permitted within30 nominal system-clock seconds after FPGA
reset. It consumes the attempt even if configuration is invalid. Before START,
configure exactly one supported period/target pair and a nonzero128-bit nonce.
After the attempt, config is immutable; no restart or fallback. Generation starts
one period after START, increments sequence for every offered record (including
full-FIFO discards), and automatically ends at the target. An early STOP freezes
actual counts without manufacturing the requested total. POP is permitted for
at most5 nominal seconds after STOP/completion. Generation and bounds use the
FPGA clock, independently of host or RP progress; they are not calibrated seconds.

| Offered16-byte record rate | Period at32MHz | Target / nominal episode |
| --- | ---: | ---: |
| 256B/s | 2,000,000 cycles | 960 /60s |
| 1,024B/s | 500,000 cycles | 3,840 /60s |
| 2,048B/s | 250,000 cycles | 7,680 /60s |

The rate counts complete16-byte source records, including their CRC; the known
pattern alone is four bytes. Report these separately from USB framing and actual
received payload. Source offered rates do not establish transport capacity.
The existing nominal32MHz **PIO instruction** clock gives about0.97MHz SCK;
SPI's half-period remains≥8 FPGA system cycles. No10/20/40MHz SCK preset is
implemented or admitted. At least six single-word transactions per record make
overhead significant; actual bridge throughput is still unknown.

Each record has four32-bit words in canonical little-endian byte order:
sequence, lower32 bits of absolute FPGA tick, known pattern, CRC32/IEEE over the
preceding12 bytes. Pattern is `seq XOR rol32(seq,7) XOR nonce0 XOR nonce1 XOR
nonce2 XOR nonce3 XOR 46534731`. This noncryptographic fixture is not ownership
proof or a collision-resistant nonce signature. The FPGA and downstream frame
must bind the full run nonce and exact image independently. CRC uses reflected
polynomialEDB88320, initial/final XORFFFFFFFF. Host tests use independent `zlib`.
Tick32 wraps after134.217728 nominal seconds; snapshots also expose64-bit ticks.
Consumers must retain wrapping/bounds explicitly, never assume monotonic uint32.

The64-record FIFO stores1KiB logical data in a synchronous read/write memory.
Actual block allocation and fit require synthesis. HEAD remains non-destructive
and stable until a matching sequence POP. A two-cycle HEAD-valid delay after an
empty enqueue or POP avoids relying on a device's same-address read/write mode.
Wrong, stale, empty, paused or overdue POP is refused and counted. Concurrent
full FIFO POP/PUSH accepts the new record without an overflow. Otherwise full
generation drops the new record, increments generated/drop counts and sequence;
it never overwrites the head or pauses the offered source to appear lossless.

## Byte-addressed register map

Global address is10000 plus the local hexadecimal offset below. Classic,
non-pipelined32-bit Wishbone accesses; aligned addresses and full-byte writes
only. One acknowledgement per assertion, held requests are not repeated. Invalid
addresses/fields produce error/refusal. SPIBone ACK/ERR remains indistinguishable,
so future RP firmware must verify state/config/POP readback, not trust ACK alone.

| Local offset | Record |
| --- | --- |
| 00 /04 /08 | ABI46534731 / requested system Hz / capabilities00074010 |
| 0c | write-only exact control:1START,2STOP,4SNAPSHOT,8one100ms POP pause |
| 10 /14 | period config / exact target config |
| 18 /1c /20 /24 | nonce words0..3 |
| 28 /2c /30 | live state / FIFO level / FIFO high-water |
| 34 /38 /3c /44 | stable head sequence / tick / pattern / CRC; zero unless valid |
| 40 /48 | write matching POP sequence / live popped count readback |
| 4c /50 /54 /58 | snapshot ID / coherent snapshot tick low/high / state |
| 5c /60 /64 /68 | snapshot generated / enqueued / full-discarded / popped |
| 6c /70 /74 /78 | snapshot refused POP / refused commands / remaining / high-water |
| 7c /80 /84 /88 | snapshot START tick low/high / STOP tick low/high |
| 8c /90 /94 /98 | accepted pause begin low/high / end low/high |

State bits0..6: attempted, running, done, HEAD-valid, pause-active, drain-expired,
START-accepted. Other bits are zero. SNAPSHOT captures one pre-edge coherent
state, all counters, start/stop and tick; subsequent source/pop activity cannot
change that bank without a new SNAPSHOT. Reads from control/POP are errors.
Nonce/period/target readbacks are configuration requests, not physical proofs.

Control8 accepts once while running and blocks POP for SYSTEM_HZ/10 cycles.
It does not stop generation or readings and preserves actual begin/end ticks;
this is an FPGA POP-refusal fault fixture. It is separate from an RP firmware
pause in drain scheduling and from a host-reader pause which may be absorbed by
OS USB buffers. It is not a sustained-success case or physical backpressure
proof. Future tests must label and measure these three controls separately.
The future bridge must reserve queue capacity before POP and compare popped
count readback to its prior count. A missing/ambiguous response must not trigger
a blind POP retry: preserve the uncertain record and reconcile popped/head and
coherent counters before continuing, or terminate with unresolved consumption.
The source never observes external high-Z or analogue pin timing.

## Offline checks and remaining artifacts

Commit these sources before generation. Use the locked `.#forgix` shell plus an
owned private Taskfile (no shared Taskfile/flake changes in this step). Simulations
instantiate the **actual** Verilog with a cycle-scaled12800Hz parameter; production
wrapper pins32000000 and exact presets. This speeds testing without changing
record totals, FIFO depth, CRC/control logic or relative5/30/60s bounds. It is
not a simulated physical bandwidth measurement.

Tests exercise every rate's full finite record sequence/ticks/CRC and POP readback,
full-drop reconciliation, stable head, stale/wrong/empty POP, coherent snapshots,
one bounded pause, invalid/late START, no restart/config changes, invalid address
and byte-mask refusal, early STOP/drain expiry, and simultaneous full POP/PUSH.
The wrapper verifies original CSR addresses, new region and unchanged pins.
It also compiles and executes the full generated top over simulated SPI pads,
including cold startup and both register regions. Held requests are exercised
for exactly one POP acknowledgement. Existing guard/register candidate
regressions still need to pass unchanged.

`tools/forgix_synthetic_gateware.py --output .scratch/<fresh-directory>` emits
private top/core RTL, memory initialization and a hash manifest. It binds all
loaded project-module inputs and the locked board/LiteX revisions. It refuses
uncommitted sources, an unrecognized toolchain, symlink/existing/outside paths. It invokes no vendor or
programmer and claims no resource/timing fit. Future builds must bind committed
core/wrapper/guard/old generator, emitted RTL/memory/CSR map, fixed32MHz constraints,
exact target grade/interface and vendor stages/bitstream hash. Independently audit
new RP ELF/SRAM allocation, startup/UID/configuration and all execution inputs.

A complete trial still needs fresh full original-flash preservation, physical
register/pin/clock qualification, reviewed exclusive identity-selected lifecycle,
FPGA→RP stream firmware/collector, and full recovery after every outcome. RP
preservation alone does not preserve unknown volatile FPGA contents. Track a
recoverable original FPGA image/state before mutation. Do not admit loads with
model-only qualification or claim factory return from an END frame.

Future accounting: generated=enqueued+full-discarded; enqueued=popped+remaining;
verified host records require independent record/frame CRC, nonce/profile and
sequence checks. Distinguish unsent RP backlog, physical transport errors and
unresolved consumption. Keep null/failed rates, all raw prefixes and stall timing.
No FPGA/RF task is checked by this source implementation.

Sources: [pinned LiteX SPIBone](https://github.com/enjoy-digital/litex/blob/8c01073afb71aa0a0709f02f8e24247589e8f5e4/litex/soc/cores/spi/spi_bone.py),
[Efinix T8v5.5 memory resources](https://www.efinixinc.com/docs/trion8-ds-v5.5.pdf),
[pinned Pico SDK PIO](https://github.com/raspberrypi/pico-sdk/blob/a1438dff1d38bd9c65dbd693f0e5db4b9ae91779/src/rp2_common/hardware_pio/include/hardware/pio.h).
The guard's detailed prospective timing contract remains in
[`forgix_spi_guard.py`](../../tools/forgix_spi_guard.py); digital simulation does
not establish electrical safety or measured oscillator/pad timing.
