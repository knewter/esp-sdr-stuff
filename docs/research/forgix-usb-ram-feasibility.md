# Forgix RAM-only USB diagnostic feasibility

Research checkpoint, October 2, 2026. **A bounded MCU-to-host synthetic USB
trial is feasible to prepare without the FPGA markings. No build or device
operation was performed in this review.** This can measure one downstream
segment of the proposed transport. It cannot establish FPGA transport,
FPGA SRAM access, ESP peripheral-DMA reachability or RF continuity, and closes
none of the original FPGA proposal's hardware gates.

## What is already established

[Physical preservation](../evidence/forgix-preservation/README.md) proves the
identified factory application, RP2350 A4/QFN60, software ROM entry, two matching
2,097,152-byte flash reads, device verification and unchanged application return.
The original SHA-256 is
`72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4`.
It does not prove replacement-image recovery or a hardware BOOTSEL bypass.

The [pinned manufacturer schematic](https://bitbucket.org/adiuvo-engineering/forgix_public/raw/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/Schematic/RP2350_FPGA_eensy.pdf),
re-downloaded and verified against the existing 203,392-byte/hash record,
separates **Y1, a 12 MHz MCU crystal**, from **Y2, the FPGA oscillator with an
unspecified ECS part suffix**. Y1 supports the MCU USB-clock assumption. Unknown
Y2 frequency and FPGA grade still prevent a justified FPGA constraints file;
they are not prerequisites for generating synthetic bytes in MCU SRAM. This is
a schematic observation, not a measurement of the connected crystal.

## What RAM-only means here

Use the already pinned Pico SDK 2.2.0 and picotool 2.3.1 through Nix. Add an
explicit ARM cross compiler/CMake/Ninja/TinyUSB source closure to the locked
flake and a build Task; do not let CMake fetch tools or submodules from the
network. The existing host picotool build is not a firmware cross compiler.

SDK [`pico_set_binary_type(target, no_flash)`](https://github.com/raspberrypi/pico-sdk/blob/a1438dff1d38bd9c65dbd693f0e5db4b9ae91779/src/rp2_common/pico_standard_link/CMakeLists.txt)
selects the RAM linker/startup route. The [RP2350 linker file](https://github.com/raspberrypi/pico-sdk/blob/a1438dff1d38bd9c65dbd693f0e5db4b9ae91779/src/rp2_common/pico_crt0/rp2350/memmap_no_flash.ld)
provides main SRAM `0x20000000..0x20080000` and two 4 KiB scratch banks ending at
`0x20082000`, including a vector table at the image start. A compiled ELF, its
map and program headers must establish the actual footprint; source size alone
does not. Proposed conservative budget: no more than 128 KiB statically allocated
main SRAM, bounded USB buffers, no heap, explicit stack reservation and no second
core.

The pinned [picotool loader implementation](https://github.com/raspberrypi/picotool/blob/2041936441b48a3cc53ae3da9e805229fe8f4e18/main.cpp)
separates flash writes from SRAM writes and requests RP2350 RAM_IMAGE boot for a
RAM-started executable. The intended operation is `load -v -x diagnostic.elf`
with freshly identity-selected bus/address. **The ELF, not the filename or
`-n`, proves the destination:** reject every loadable file range outside ordinary
SRAM, flash/XIP/OTP/peripheral destinations, malformed or overlapping ranges,
out-of-bounds BSS/stack, and non-RP2350 ARM/no-flash metadata. Do not use raw BIN
with an implicit address, flash offsets, partition overrides, OTP or erase.

## GPIO and recovery constraints

Disable UART explicitly. Call USB initialization directly rather than enabling
default peripherals. No LED, SPI, PIO, FPGA reset/configuration, oscillator-enable
GPIO or PSRAM routines belong in this image. Audit the final linked image and
SDK startup before loading. The [SDK runtime](https://github.com/raspberrypi/pico-sdk/blob/a1438dff1d38bd9c65dbd693f0e5db4b9ae91779/src/rp2_common/pico_runtime_init/runtime_init.c)
resets ordinary IO peripherals during startup: zero application GPIO calls
does **not** guarantee unchanged prior electrical pin states. An RP reboot can
release outputs to their reset state; describe that boundary explicitly.

The pinned [factory main](https://bitbucket.org/adiuvo-engineering/forgix_public/raw/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/BitStream_Loader/firmware/pico/src/main.c)
initializes USB, and FPGA control-pin setup occurs in
[`fpga_config_begin`](https://bitbucket.org/adiuvo-engineering/forgix_public/raw/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/BitStream_Loader/firmware/pico/src/fpga_config.c)
when the programming transaction starts. Existing preservation sent HELLO/STATUS,
not START. Still verify present idle ownership and any external connections
before a trial; do not claim unchanged FPGA state from absence of START alone.

Use a finite watchdog and nonblocking USB producer. The
[SDK watchdog implementation](https://github.com/raspberrypi/pico-sdk/blob/a1438dff1d38bd9c65dbd693f0e5db4b9ae91779/src/rp2_common/hardware_watchdog/watchdog.c)
supports regular flash boot with `watchdog_reboot(0, 0, delay_ms)`; a fed watchdog
must have an independent maximum experiment deadline. Enable it at the earliest
reviewed point, before USB initialization, and feed only bounded progress before
that deadline. A watchdog in `main` cannot recover a hang during earlier runtime
initialization. Keep the existing software-reset USB interface when compatible,
but do not depend on functioning USB for recovery. A physical unplug/replug
returns to unchanged flash if SRAM loading fails; root must be able to obtain
that action if startup never reaches its watchdog. PROGRAM and the FPGA button
remain unproved substitutes for BOOTSEL.

## Concrete next preparation

Prepare, then independently review, a host-only build plus ELF preflight for a
finite synthetic USB CDC producer. Give it an explicit distinct product string,
protocol version, build hash and per-run nonce. Use fixed-size binary records
with sequence, declared length, device timestamp, deterministic payload and CRC.
Use binary writes with no printf/debug text or CRLF conversion on the data
channel. Choose and review a single TinyUSB scheduling owner; a custom direct
TinyUSB producer must not race the SDK stdio background worker.
Keep counters for generated/enqueued bytes, partial writes, backlog high-water,
discarded records and USB stalls. Host receipts independently verify sequence,
payload, CRC and monotonic timestamps; framing recovery must retain damaged
prefixes instead of silently dropping them.

Prospective candidate rates are 64, 256 and 768 KiB/s for 60 seconds each, with
one explicit 100 ms host pause at each rate. The fastest is below the documented
1.5 MB/s USB wire bound, but success remains unmeasured. A small bounded queue
may overflow during a pause: record this outcome and exact loss rather than
pretending it is a FIFO/SRAM feasibility result. Require actual host payload per
elapsed time, total integrity results, gap/backlog and stall distributions.
These values are proposed experiments, not accepted transport guarantees.

Before hardware: fresh factory identity/HELLO/STATUS; exclusive operator lock;
private backups present and hash-valid; frozen SDK/TinyUSB/tool/image hashes;
reviewed SRAM-only ELF; fixed finite lifetime; explicit recovery route. Start the
host reader before enabling the producer. After every outcome, close and reap
all owned processes, serial/libusb handles and scoped containers, return to the
original factory identity, verify the saved flash against the device through
targeted ROM entry, return again, and check HELLO/STATUS ready/idle. An unchanged
backup file alone is not proof flash stayed unchanged.

**Recommendation:** proceed with that offline build/preflight implementation
after root reviews this plan. Do not run a physical trial until its lifecycle and
recovery checks are reviewed. FPGA oscillator/grade/revision and ESP-to-Forgix
wiring remain necessary for the later SPI/FPGA leg. A useful MCU USB result only
narrows the host-link budget for bounded snapshots, spectra or events.

Source receipts: schematic SHA-256
`364ff65046fd3932c8ab8e9acc95e542da2712e0b880dbbc78bb6afe1d6ce4de`;
factory main `ee89cc0d201737ccabacca79d0fdeb3bd994a165578ae0289e1ba5ea209b23d1`;
factory FPGA helper `9aa9674c328cec6603f235e3398a3f4621a94a42868d901c034008c98df26246`;
picotool main `10f28c2e60057d309e0206b54bfc61a7f27a5bad66134661c087b5c81571a5fd`.
No device identities or raw flash bytes are included.
