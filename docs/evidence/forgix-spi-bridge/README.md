# Forgix register bridge: offline preparation

October 3, 2026. **The RP bridge and guarded FPGA gateware compile. No FPGA
was programmed, no RAM bridge was loaded, and no hardware port was opened in
this follow-up.** Physical register readback and the FPGA feasibility gates
remain open. Previous [fresh MCU preservation](../forgix-toolchain/README.md)
is retained; it does not identify the physical FPGA grade or prove SPI timing.

## Actual build and artifact audit

The locked `.#forgix-spi-bridge` shell and `task forgix:spi-bridge:build` produced
bridge008 from source commit `a2995d769d1942714218d1a2388239160f061cc8` in
20.58 seconds. Pico SDK2.2.0, exact TinyUSB revision86ad6e56, ARM GCC15.3.Rel1
and SDK pioasm2.2.0 come from Nix. The ELF has **27,968 allocated SRAM bytes**,
an explicit4KiB core0 stack, no core1/heap allocation and RP2350 ARM no-flash
metadata. ELF file size620,444 bytes includes nonloaded debug information.

ELF SHA256: `025d367aec734ad45be6e0709b9074bc7665e87c1abb35bb8d259f3cd776d7eb`.
Private build manifest SHA256:
`f9c80d7297c245881777e9b6a97ed997ad5201db40020488fa0b8c15443eda27`.
The [own-operator artifact audit](artifact-audit.json) checks committed inputs,
every exported artifact hash, load layout, embedded PIO words and a freshly
assembled RP2350-version1 header. This is not independent-agent review or
whole-program/physical electrical proof. Loading admission stays false.

Separate independent review passes bridge008's source/artifact bindings,
layout, embedded instructions, linked reset audit and finite host engine.
Private review receipt SHA256:
`354d1320ec9ba11150f45e8230f017bf6a525741625854bc3152a7b287e2567d`.
Its conclusion is **offline preparation only**. Physical timing, linked startup,
configuration continuity and the complete load/recovery lifecycle remain open.

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
fractional-divider jitter or metastability proof. Current CI runs 29 tests: 28 pass and the Migen integration test explicitly
skips. This includes 11 deadline/init-failure regressions against actual C
transaction functions using a mocked SDK and nine host-engine checks against
fragmented replies from the compiled C protocol (fake register bank/transport). The original
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

Independent review then rejected bridge004's deadline behavior: an already-ready
PIO flag or FIFO could bypass elapsed-time checks; init failures were ignored.
The retained actual-C regression reproduced 10 failures and one timely baseline
pass. Bridge006 checks ready stages, init results and late acceptance, caps the
transaction deadline at the 120-second lifetime, and uses fresh ARM time. All 11
regressions now pass independently. These are software polling/acceptance
bounds, not CPU-stall-independent physical pin-abort deadlines. The 2-second
watchdog is a separate fallback; an already-issued scratch write cannot be
rolled back. Failed builds and bridge004 review/reproducer remain retained.

## Host engine and startup transition

`RegisterRun` now saves scratch, checks all three patterns and advancing counter
(including wrap), restores/readbacks scratch, and verifies FINISH. It retains
partial requests/replies in memory. Valid semantic failure still attempts
restore/FINISH; ambiguous framing, source/nonce/sequence/status, late replies or
transport failure poison the session without retry or guessed cleanup. Failed
restoration cannot report success. Cancellation propagates with the failed
summary. Five additional independent late-frame/parser/cleanup/cancellation
probes pass. This injected-transport engine opens no port. The subsequent
[private collector](../forgix-spi-collector/README.md) now implements prefix
persistence, caller-supplied lock/enumeration checks and transport closure,
with 15 own-operator C/PTY/fault tests. The subsequent
[lifecycle controller and worker wrapper](../forgix-spi-lifecycle/README.md)
pass offline/process checks. The physical backend and complete measured
load/recovery path remain unimplemented. FINISH acknowledgment
alone is not factory return.

The [actual linked startup audit](startup-audit.json) recognizes the saved
bridge008 reset instruction sequence and initializer-table bindings. It binds
the exact SDK NAR and reset metadata: GPIO, pads and PIO0 are reset before main.
For GPIO1/2/3/4/5/19, the SDK documents null function31, pad isolation and enabled
pull-down at reset. External physical levels are unmeasured. The main watchdog
starts afterward. This narrow audit is not full boot-ROM/startup control-flow
or electrical proof. Four independent mutated-ELF probes refuse altered code,
reset masks or initializer bindings.

The lifecycle must qualify configuration retention through that transition or
configure the exact guarded image after RAM startup. Neither configuration
continuity nor the complete physical load/recovery path is admitted yet.

## Next physical gate

The [bridge source and protocol](../../../firmware/forgix-spi-bridge/README.md)
allow only counter reads at0x1000 and scratch read/write at0x1004, with bounded
PIO and a finite watchdog/lifetime. An offline plan saves original scratch,
checks three patterns/counter progression, then requires original-scratch
restore/readback and FINISH. The private collector has no physical trial CLI.

Before loading, qualify the fitted FPGA suffix, actual clock/connectivity and
electrical handoff, and independently review linked startup plus the complete
identity-selected, preservation/configuration/RAM-load/recovery lifecycle.
CDONE alone cannot identify the FPGA image. The bridge has no configuration
writer; the lifecycle must bind the exact guarded bitstream. Physical timing,
full original-flash/factory return and transport continuity need their own
records. No ESP wires or RF equipment are needed for the first register test.
OpenSpec remains **1/5 tasks complete**.
