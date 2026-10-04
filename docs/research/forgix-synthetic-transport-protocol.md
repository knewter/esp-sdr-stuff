# Finite FPGA-to-host synthetic transport

UNVERIFIED prospective implementation for FPGA task 2.1. This is separate from
the existing counter/scratch register ABI and the measured MCU-only USB trials.
No FPGA stream has been loaded or measured. Admission still requires the
matching preserved Forgix, physical grade/clock/pin qualification, actual linked
artifacts and independent complete configuration/load/recovery review.

The selected boundary is FPGA generator/FIFO → guarded onboard SPIBone → RP
SRAM queue → USB CDC → host. It requires no ESP wiring. It does not establish
ESP radio-SRAM access, continuous acquisition or an RF integration.

## Clock and offered-rate contract

Keep the existing conservative PIO preset first: nominal 32 MHz **instruction**
clock, approximately 0.97 MHz SCK with the actual 33-cycle bit loop. The FPGA
guard requires at least eight system cycles per SCK half-period. At nominal
32 MHz system clock that bounds SCK to at most 2 MHz before other timing limits.
The earlier 10/20/40 MHz suggestions are therefore superseded for this guarded
route; none were measured. Additional wire presets require their own timing
qualification. A divider or oscillator marking is not a measured clock.

| Offered record payload | Records/s | Nominal FPGA period | 60-second target |
| --- | ---: | ---: | ---: |
| 256 B/s | 16 | 2,000,000 cycles | 960 |
| 1,024 B/s | 64 | 500,000 cycles | 3,840 |
| 2,048 B/s | 128 | 250,000 cycles | 7,680 |

These are offered rates, not qualified delivered capacities. Record the actual
rate and elapsed cycles, including failed conditions. Fixed 64-byte SPI response
drains, status reads, CRC work and USB scheduling impose substantial overhead;
clock/8 is not the application throughput.

## FPGA source and FIFO

Use a separate versioned transport ABI and generated CSR-map check. Preserve
counter/scratch addresses 0x1000/0x1004. A record contains four little-endian
32-bit words: generated sequence, FPGA tick, deterministic nonce-bound pattern,
and CRC32/IEEE over the first 12 bytes. SPIBone bus words remain big-endian;
the conversion must be explicit. CRC uses reflected polynomial 0xedb88320,
initial/final XOR 0xffffffff; the independent check vector is
`123456789` → `cbf43926`.

A 64-record FIFO uses 1,024 payload bytes. Head reads are stable and
non-destructive until a POP supplies the matching sequence. Wrong, stale and
repeated POP requests are refused and counted. Confirm mutation by readback;
SPIBone ACK and ERR are not sufficient to distinguish success. Full FIFO causes
explicit drops with advancing source sequence, never overwrite or automatic
generator throttling. Concurrent enqueue/POP semantics must pass actual HDL
simulation and synthesis memory allocation must be inspected.

START is one-shot from idle with empty FIFO and valid nonce/rate/count. STOP
and finite completion freeze generation while preserving queued records for
bounded draining. Coherent snapshots retain generated, enqueued, full-drop,
popped, refused-pop, remaining and high-water counts, state, first/last ticks
and snapshot generation. Handle 32-bit tick wrapping explicitly; nominal
32 MHz wraps in 134.218 seconds. No ambiguous wrap interpretation is accepted.

## RP and host path

A separate RAM-only bridge autonomously drains the FPGA after START, with one
TinyUSB owner, no heap or active core1, bounded SPI operations and safe
CS-high/DATA-input cleanup. Independently validate each source CRC before POP;
reserve an RP queue slot first. A proposed sixteen-frame, 512-byte queue costs
8 KiB, subject to an actual linked SRAM/map audit with the embedded image and
4 KiB stack. Existing 128 KiB profiles remain unchanged; the separate
configuration profile retains its 256 KiB guard. Do not assume PSRAM or DMA.

USB batches carry complete source records plus separate frame CRC, nonce,
frame sequence, exact lengths/counts, explicit zero padding and device timing.
Flush partial batches on a bounded timer. Independently check source CRC and
frame CRC at the host. Retain malformed/partial prefixes, gaps, duplicates,
reordering and counter discrepancies; stop on ambiguous consumed operations.

Preserve the 120-second firmware lifetime and two-second watchdog. Configure
and reach START within the first 30 seconds; generate for 60 seconds and drain
for at most five seconds. Late readiness fails rather than extending lifetime.
Interleave USB/watchdog progress between bounded transactions. Pre-main startup
remains outside the application's watchdog scope.

## Measurements, review and recovery

Each rate retains all frames, source/RP/host counters, payload and framing
bytes, per-second throughput, FIFO/RP high-water marks, host read gaps, actual
stall intervals and final backlog. Reconcile generated = enqueued + full-drop
and enqueued = popped + remaining. Separately account for verified RP records
not delivered and ambiguous transport outcomes. Missing data is not automatically
confirmed FPGA overflow.

Predeclare a 100 ms host-reader pause at 30 seconds and measure its actual
duration. A separate 100 ms RP-drain pause exercises the FPGA queue explicitly;
host pauses can be absorbed by OS/USB buffers. A declared overflow positive
control tests drop accounting, not lossless capacity. Keep unsuccessful rates
and zero observed stalls. Digital edge/guard counters and transaction brackets
do not prove analogue setup/hold, external high impedance or calibrated frequency.

Implement in order: FPGA generator/FIFO/CRC and meaningful HDL fault tests;
independent actual-C/host codecs and corruption tests; finite RP engine;
actual vendor/ELF/startup/UID/image audits; independent whole physical backend
and recovery review. A new production qualification binds this profile rather
than borrowing an old registry tuple. There is no admitted physical streaming
command today. Before each eventual trial refresh full original preservation;
after every outcome close all ownership, return factory, reread the complete
original flash and verify factory ready/idle. Unknown closure freezes access.
No flash or OTP mutation is proposed. Preserving RP flash alone does not preserve
an unknown volatile FPGA image; its recoverable state remains a separate gate.

## Primary references

- [Pinned LiteX SPIBone](https://github.com/enjoy-digital/litex/blob/8c01073afb71aa0a0709f02f8e24247589e8f5e4/litex/soc/cores/spi/spi_bone.py)
- [T8 datasheet v5.5](https://www.efinixinc.com/docs/trion8-ds-v5.5.pdf)
- [Pinned Pico SDK PIO definitions](https://github.com/raspberrypi/pico-sdk/blob/a1438dff1d38bd9c65dbd693f0e5db4b9ae91779/src/rp2_common/hardware_pio/include/hardware/pio.h)
- [Current physical inventory and earlier suggestions](../evidence/fpga-inventory/README.md)
- [Register configuration/recovery protocol](forgix-spi-register-trial-protocol.md)

Hardware tasks remain unchecked. This preparation supports the original
several-rate transport evaluation without replacing its physical proof.
