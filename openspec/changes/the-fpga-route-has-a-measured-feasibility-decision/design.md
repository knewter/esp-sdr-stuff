## Context

See [proposal](proposal.md) for the problem and scope. The hardware identity is recorded separately from untested reception and transport behavior.

## Goals / Non-Goals

**Goals:** A measured go/no-go decision for a useful FPGA transport or processing role, not a predetermined continuous SDR.

**Non-Goals:** No promise of 80 MS/s streaming on LX6; no blind reuse of S3 dedicated GPIO/SIMD; no arbitrary transmitter.

## Decisions

The original chip lacks the S3-specific fast lane used by eSpDR. Benchmark SPI/I2S or decimated/FFT output on LX6 first. An FPGA can buffer or process data only after the ESP exposes it. Keep an S3-plus-FPGA design as a separate outcome if the original chip is the bottleneck.

The host records revisions/settings/results; firmware owns modem and memory access; an FPGA, if selected, owns only its explicitly measured transport/processing boundary.

## Concrete FPGA candidates

Forgix is a small Trion T8F49 + RP2354 design with USB 1.1, not the DDR/FT600 USB 3 route in eSpDR. Start with bounded counters, FIFOs, triggering or decimation over verified SPI pins. Its PSRAM belongs to the board architecture; do not assume it is directly usable as a high-rate FPGA sample buffer.

The host PCIe device dabc:1017 is associated with AS02MC04/XCKU3P in prior local notes. Treat that as an identification candidate. Confirm markings and a reversible JTAG/PCIe bring-up path before any programming or DMA benchmark. Record available FPGA memory independently of PCI BAR sizes.

[Inventory and provenance](docs/evidence/fpga-inventory/README.md), [Adiuvo design](https://forgix.tech/) and [primary LiteX example](https://github.com/enjoy-digital/aduivo_forgix_test).

## Risks / Trade-offs

SRAM ownership/capture gaps may remain even with faster output. Electrical compatibility, clocks and available GPIO are unknown until inventory. Two hundred MB/s is payload, not bus line rate.

## Validation and decision

An inventory plus sustained payload, loss/backlog and timing measurements. 80 MS/s × 20 bits requires 200 MB/s before framing; lower-rate or spectral output alternatives get separate budgets.

Inventory is the first proof artifact. The benchmark command is selected only after its hardware interface exists; acceptance requires timestamped sequence/CRC counters and a measured sustained rate, not peak link marketing. RF integration is conditional on measured synthetic feasibility.

## Visual plan

[Experiment flow and provenance](docs/design/the-fpga-route-has-a-measured-feasibility-decision/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.

## Implementation findings

[The feasibility checkpoint](docs/evidence/fpga-inventory/README.md) separates current USB/PCI observations, pinned primary design review, and generated capacity calculations. It identifies a bounded completed-snapshot SPI path; direct RF SRAM DMA and continuous acquisition are not established. Forgix USB cannot sustain the raw 80 MS/s stream; a filtered lower-rate or event/spectrum path still needs a real benchmark. Physical board grade/clock mismatches against LiteX and an unavailable verified FPGA host transport keep later gates open.

The [local toolchain setup](docs/research/forgix-toolchain.md) now provides
Task commands for completed-download discovery, private permanent staging,
versioned Linux installation and execution through the locked Nix FHS runtime.
Fifty-one focused installer/compiler tests pass. [Actual installation evidence](docs/evidence/efinity-install-001/README.md)
now verifies Efinity 2026.1.132 installation, repeat reuse, real vendor CLI and
full host/vendor checks inside Nix FHS after a retained Python-environment
failure was corrected. A [complete generic T8F81/C2 compiler test](docs/evidence/efinity-compile-smoke-002/README.md)
now verifies all four stages and a fresh bitstream under the present licensing
configuration. The initial skipped-interface/no-bitstream failure is retained;
Nix supplies the missing SQLite and D-Bus libraries. This software example
does not establish the connected T8F49 Forgix constraints or image. This setup
closes no physical inventory or transport benchmark task.

The [RAM-only USB feasibility review](docs/research/forgix-usb-ram-feasibility.md)
identifies a separate way to prepare the MCU-to-host segment before FPGA
markings arrive. It distinguishes the schematic MCU crystal from the unknown
FPGA oscillator and requires a pinned build, actual SRAM-only ELF audit,
finite watchdog, startup/pin review, physical recovery availability, fresh
flash verification and factory return. Preparation and any later USB-only
measurement do not prove the selected FPGA transport or close its gates.

The user now reports USB-only attachment and can replug. An
[actual offline RAM producer build](docs/evidence/forgix-usb-ram-build/README.md)
and [independent artifact review](docs/evidence/forgix-usb-ram-independent-review/README.md)
verify 35,948 bytes of ordinary-SRAM allocation and bound the historical build
inputs. The [prospective first USB protocol](docs/research/forgix-usb-ram-trial-protocol.md)
selects one 64 KiB/s, 60-second condition with a measured 100 ms host pause.
Lifecycle/collector review and fresh device preflight still precede any load.
Pre-main startup is outside the watchdog and SDK IO resets can change pin states;
physical recovery availability is not a successful recovery measurement.

The [first physical RAM episode](docs/evidence/forgix-usb-ram-trial-001/README.md)
stopped before loading: factory serial open hit a USB DTR-control timeout,
and its bounded owned worker was reaped. No payload condition or ROM/RAM
operation ran. USB enumeration alone does not verify the factory application
or original device flash; explicit recovery awaits a physical replug.
The [lifecycle review](docs/evidence/forgix-usb-ram-lifecycle-review/README.md)
and [actual version-check supplement](docs/evidence/forgix-usb-ram-version-review/README.md)
establish offline preparation only. The original task gates remain open.

## Current register-trial implementation boundary

Later [MCU USB measurements](docs/evidence/forgix-usb-ram-recovery/README.md)
retain verified recovery and a lossless 64 KiB/s condition; requested 256 KiB/s
loses 431 records, matching device discards. These are MCU-to-host measurements,
not a selected FPGA transport benchmark. They supersede the initial episode's
replug requirement without closing tasks 1.1 or 2.1–2.3.

The [compiled bridge and linked startup audit](docs/evidence/forgix-spi-bridge/README.md)
show that SDK GPIO/pad/PIO resets precede main. The lifecycle must qualify
retention of the exact guarded image through that transition, or configure
that image after RAM startup. CDONE alone cannot identify the image. The
current bridge has no configuration writer; the latter strategy still needs
reviewed firmware/protocol implementation and physical qualification.

The [private collector](docs/evidence/forgix-spi-collector/README.md) retains
failed raw prefixes and checks serial closure. The
[offline lifecycle controller](docs/evidence/forgix-spi-lifecycle/README.md)
now enforces preservation-before-mutation, configuration/image matching,
recovery after possibly consumed requests, and no further access after unknown
worker closure. Its 600-second model reserves 325 seconds for cleanup and full
verification. Actual process tests verify inherited-lock and whole-group
cleanup using regular-file fixtures. Adapter receipt/clock tests are not
physical preservation or FPGA proof.

No physical backend or load/program CLI is admitted. Before a hardware trial,
bind the measured board grade/clock/timing, reviewed FPGA and RAM artifacts,
frozen Nix execution inputs, original USB identity, fresh full preservation
and an independently reviewed configuration/load/recovery path. Acceptance
still requires physical register readback and later sequence/CRC, sustained
payload, loss/backlog and timing measurements. Host preparation does not
narrow those requirements or move unverified behavior into the accepted ledger.

## Exact-image configuration after RAM startup

An opt-in bridge build now embeds the complete decoded Efinity hex candidate
in RAM and exposes a separate `FGSC` handshake before register ARM. Build-time
hashes bind both the original hex and decoded bytes to the compiled identity;
the request must match that image hash. One configuration attempt is allowed
within the first 30 seconds, with a 20-second operation cap. The register-only
variant keeps its existing protocol and has no configuration writer.

The candidate follows the pinned factory's mode-3 MSB-first, oscillator/reset
delays and 32 trailing zero bytes, using software clock edges with per-bit
deadlines instead of an unbounded blocking SPI call. It requires CDONE low
during reset and high after all bytes. CS goes high before the shared data pin
is released. Actual clock frequency, pad timing, pin ownership, electrical
behavior and the image's hardware identity still require qualification.

The full decoded prefix is retained, matching the factory host parser. The
image is capped at 192 KiB. A separate `spi-config-bridge` application profile
has a 256 KiB ordinary-SRAM allocation guard and requires configuration/image
symbols. The existing USB and register-only guards remain 128 KiB. All variants
still require no flash writer, no heap, inactive core1 and a 4 KiB core0 stack.
This explicit software budget does not admit loading an image onto hardware.

The host handshake accepts caller-owned transport and persists intent and
response prefixes; it supplies no device CLI. Its reply verifies matching
nonce/image/source and a configuration indication, not measured configuration
continuity. Physical backend, independent load/recovery review, fresh full
preservation and acceptance measurements remain outstanding. Checkboxes and
the accepted ledger remain unchanged.

## Identity-selected backend preparation

The later [backend preparation](docs/evidence/forgix-spi-backend/README.md)
implements an adapter for the existing helpers with admission still disabled.
Every hardware method requires an admitted session and a committed qualification
tuple; the registry is empty. It supplies only an offline plan CLI. USB
container/process ownership stays at the root, while serial calls are contained
in bounded inherited-lock workers. Aggregate closure covers both resources.
Qualification registry and backend source are separate frozen inputs so an
artifact tuple can bind the backend hash without a self-referential hash.

The new bridge USB serial comes from the pinned SDK RP2350 ROM chip-info
constructor. It executes before main and the watchdog; Release removes its
return-code assertion. The host requires the normalized UID hash and unchanged
enumeration before/after configuration and during collection. This selector
behavior and own-operator fault fixtures are not physical UID continuity or
configuration-transition proof. Independent whole-backend review and production
coordinator admission remain required before any physical episode.

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

## Selected synthetic stream implementation

The [finite transport protocol](docs/research/forgix-synthetic-transport-protocol.md)
reconciles task 2.1 with the actual guarded SPI path. The register-only bridge
allows 24 one-word commands and cannot be repurposed as a sustained stream.
A separately versioned FPGA source/FIFO, RP autonomous drain and framed USB
collector are required. Preserve the old register ABI and its qualification
scope. The proposed new source has a separate Wishbone region at 0x00010000;
its generated exact map must match its declared ABI before a candidate build.

Start with 16-byte sequence/tick/pattern/CRC records, a 64-record stable-head
FIFO, matching-sequence POP with readback, coherent counters and finite
256/1,024/2,048 B/s offered conditions for 60 seconds each. These are prospective
rates, not delivered capacities. Distinguish host-reader, RP-drain and FPGA
POP-refusal controls; none substitutes for another. Preserve overflow and
unresolved transport outcomes rather than throttling the offered source.

The existing nominal 32 MHz PIO instruction clock produces approximately
0.97 MHz SCK. At nominal 32 MHz FPGA clock the current eight-cycle half-period
guard bounds SCK to at most 2 MHz before other limits. Earlier 10/20/40 MHz
suggestions are superseded for this route and remain unmeasured. Several offered
rates at one qualified wire preset meet the transport question without
pretending a fast divider is qualified. Actual image, SRAM, startup, UID,
physical timing, frozen inputs and complete recovery review precede admission.
No ESP wiring is needed for this synthetic boundary; RF integration retains
its own conditional physical gates. Tasks 1.1 and 2.1–2.3 remain unchecked.

## Reviewed implementation prerequisites

The [finite codecs](docs/evidence/forgix-synthetic-codec/README.md) pass actual native-C/Python and independent fault replay after a retained overlapping-output correction. The [compiler route](docs/evidence/forgix-synthetic-compiler/README.md) retains its first actual FHS failure before generation: committed-input verification requires Git, now explicitly supplied by Nix. Runtime verification, actual vendor compilation/report review, RP stream, physical qualification and complete recovery remain gates. No transport task is accepted.

## Actual routed failure and reviewed correction

The [actual compiler reports](docs/evidence/forgix-synthetic-compiler/README.md) fit the requested target resources but miss internal 32 MHz setup by 0.694 ns. Exact vendor XML rewrite and empty-auxiliary inventory corrections pass review. The [deadline-register optimization](docs/evidence/forgix-synthetic-timing/README.md) preserves cycle behavior in actual differential HDL tests. Fresh routed timing, RP/host stream, physical grade/clock/pins and complete recovery remain gates; no task is accepted.
