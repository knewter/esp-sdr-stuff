# Forgix register bridge: offline preparation

October 3, 2026. **The RP bridge and guarded FPGA gateware compile. No FPGA
was programmed, no RAM bridge was loaded, and no hardware port was opened in
this follow-up.** Physical register readback and the FPGA feasibility gates
remain open. Previous [fresh MCU preservation](../forgix-toolchain/README.md)
is retained; it does not identify the physical FPGA grade or prove SPI timing.

## Actual build and artifact audit

The locked `.#forgix-spi-bridge` shell and `task forgix:spi-bridge:build` produced
bridge004 from source commit `2f86290a319ca037baac3dc6b857d462bd5fb72a` in
9.99 seconds. Pico SDK2.2.0, exact TinyUSB revision86ad6e56, ARM GCC15.3.Rel1
and SDK pioasm2.2.0 come from Nix. The ELF has **27,616 allocated SRAM bytes**,
an explicit4KiB core0 stack, no core1/heap allocation and RP2350 ARM no-flash
metadata. ELF file size618,148 bytes includes nonloaded debug information.

ELF SHA256: `c8c3da4cb4748054d256db645f23d068b6eff4272396079d98f3017d78f0b22d`.
Private build manifest SHA256:
`e36c1c5b2e0b52cf13c2f5b7a105910d81aebb46016b4fc1f3f27729f95bf928`.
The [own-operator artifact audit](artifact-audit.json) checks committed inputs,
every exported artifact hash, load layout, embedded PIO words and a freshly
assembled RP2350-version1 header. This is not independent-agent review or
whole-program/physical electrical proof. Loading admission stays false.

The request program has12words and the response program7words. The actual
linked instruction arrays match those used in the passing simulation. The
first test assembly used version0 metadata; version1 produces identical
instruction words, and the current test command explicitly requests version1.
Neither program uses newer-version instructions. The strict original USB
producer policy still refuses this GPIO/PIO bridge image.

## Meaningful host checks

Nine tests pass in the FPGA-capable Nix shell (258.07seconds, no skips): real
compiled C protocol against the independent Python codec; corruption of every
request byte; reserved fields, nonce/order/replay and24-command bound;
arbitrary/reset-register refusal; delayed0xff/header/payload parsing; CRC and
source identity rejection; default-layout-policy separation; assembled final
zero-bit/OE timing; and actual PIO instruction words driving GuardedSPIBone.

The integration test runs scratch write/readback and two advancing counter
reads across four nominal clock phases, with delayed Wishbone ACK and CPU
handoff stalls. It detects modeled RP/FPGA output contention and verifies no
Wishbone request precedes the handoff. This is a digital instruction-subset
model, not physical PIO, pad timing, input synchronization, FIFO-full stalling,
fractional-divider jitter or metastability proof. Current CI repeats eight
host/PIO checks and explicitly skips the Migen integration test. The original
USB layout-policy suite also passes13tests.

## Retained failures

Bridge001 linked successfully but failed artifact export: the SDK emitted
`.elf.map` rather than the assumed `.map` filename. Bridge002 exported artifacts
but failed the mandatory loadable identity guard because link garbage
collection discarded the unused profile. Bridge003 failed compilation because
the ARM target ignored the `retain` attribute under `-Werror`. Bridge004 keeps
the exact profile through a GNU linker undefined-symbol root and passes the
unchanged identity requirement. All failed directories/manifests/logs remain
private and unchanged; none opened hardware. The initial standalone pioasm
invocation also refused because the SDK package exports no executable; a
separate SDK-pinned Nix pioasm derivation supplies it.

## Next physical gate

The [bridge source and protocol](../../../firmware/forgix-spi-bridge/README.md)
allow only counter reads at0x1000 and scratch read/write at0x1004, with bounded
PIO and a finite watchdog/lifetime. An offline plan saves original scratch,
checks three patterns/counter progression, then requires original-scratch
restore/readback and FINISH. It is not a serial trial runner.

Before loading, qualify the fitted FPGA suffix, actual clock/connectivity and
electrical handoff, and independently review linked startup plus the complete
identity-selected, preservation/configuration/RAM-load/recovery lifecycle.
CDONE alone cannot identify the FPGA image. The bridge has no configuration
writer; the lifecycle must bind the exact guarded bitstream. Physical timing,
full original-flash/factory return and transport continuity need their own
records. No ESP wires or RF equipment are needed for the first register test.
OpenSpec remains **1/5 tasks complete**.
