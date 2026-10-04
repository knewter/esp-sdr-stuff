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

## Prospective one-way clock bootstrap

Prepare the [distinct one-way observer](docs/research/forgix-clock-observer-protocol.md)
to remove the first-read SPI clock dependency. Reset-safe finite F2 output and
RP input-only PIO measure a relative clock interval. Source tests are possible
offline; root-owned new builds, four-pin/startup audits and preserved measurement
lifecycle require independent review before loading. Fitted grade/revision,
electrical/attachment/recovery gates remain. No original artifact or registry
changes, absolute calibrated MHz claim or physical checkbox completion.

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

[Actual attempt004](docs/evidence/forgix-synthetic-compiler/README.md) now passes
independent exact-artifact review and modeled internal 32 MHz timing (+1.530 ns
setup, +0.642 ns hold). Physical grade/clock/SPI timing remain unqualified. The
separate RP stream ARM build passes its initial layout guard at 220,200 SRAM
bytes; actual artifact/startup and collector/lifecycle review remain gates.
No hardware checkbox or accepted requirement changes.

The [actual RP stream artifact](docs/evidence/forgix-synthetic-stream-artifact/README.md)
now passes independent complete image/PIO/layout and selected linked-path review,
six actual-ELF mutation groups and seven recognized startup-audit groups. SRAM
allocation is 220,200 bytes. Complete admitted collector/lifecycle and physical
grade/clock/pin/ownership/recovery gates remain; no task is accepted.

The [corrected host collector](docs/evidence/forgix-synthetic-host-collector/README.md)
passes 32 author groups and three independent retained fault probes. Rejection
is permanent, final source snapshots are monotonic, and observed FPGA completion
is distinct from RP clock duration. Complete identity-selected worker/lifecycle
integration and physical qualification remain; no hardware task is accepted.

## Distinct synthetic lifecycle implementation prerequisite

Implement a separate registry-gated synthetic-stream coordinator/backend. The
register collector, its 24-command route, registry and artifact profiles remain
unchanged. One contained inherited-lock worker owns PID4013 USB selection and
CONFIG/START/DATA/END, binding the checked original UID, full nonce, compiled
build identity, embedded image and exact finite profile. Saved raw replay must
agree with a lossless terminal receipt; accounted losses remain failed.

Freeze committed transitive execution inputs, immutable Nix/container/runtime
and complete artifact/export bindings. Freeze the empty synthetic qualification
registry separately from the reviewed tuple to avoid circular hashes. A durable
pre-access lease and the shared unknown-resource marker are rechecked under the
one global flock. The 600-second acceptance clock includes durable receipt
writes and reserves 325 seconds for factory/full-original readback recovery.
Initial preservation can change USB mode; its intent therefore requires recovery
even if it fails. Every possibly consumed load/configuration/START failure must
recover after verified whole-group/container closure. Unknown closure prohibits
further device access and retains the lease for operator investigation.

Test actual inherited locks, process death, blocked workers/descendants,
cancellation, late receipts, storage errors and failed preservation/recovery,
plus strict stream identity/schema and artifact refusal. Offline tests admit no
physical episode. Physical grade, measured clock, voltages, pin ownership,
loading/recovery and selected-transport measurements remain required; tasks
1.1 and 2.1–2.3 and the accepted ledger are unchanged.

## Complete offline synthetic lifecycle checkpoint

The [separate production stream lifecycle](docs/evidence/forgix-synthetic-lifecycle/README.md)
now passes 35 author and 18 independent groups, including actual compiled-C
wire/replay, real process/lock/death fixtures and explicit known-closed recovery.
It binds PID4013, original UID/full baseline, exact RP/image/full nonce/profile,
62 execution files and verified immutable runtime. Its registry remains empty.
One shared durable lease and a 600-second persistence-inclusive acceptance
clock protect preservation/load/CONFIG/START/END and factory/full-original
verification. Recovery rotates the lease before access and cannot reload/start;
unknown or missing closure prohibits all further access without an override.

Existing ARM001 metadata was checked read-only; no new build, device operation,
loading or FPGA/RF measurement occurred. Physical inventory, measured clock,
voltages/pin timing/handoff, loading/recovery and several-rate transport proof
remain gates. Tasks 1.1 and 2.1–2.3 and accepted requirements are unchanged.

An additive actual POSIX PTY audit found bulk-read bytes hidden by a subsequent
EIO. The synthetic-only bytewise correction retains returned prefixes across
errors, interruption and late returns; seven new independent groups replayed
with the original eleven. This narrows software uncertainty only: unread or
lower-level lost bytes and physical transport remain unqualified. Historical
source/proofs and all physical checkboxes are retained.

## Synthetic host dispatch binding (prospective)

UNVERIFIED implementation prerequisite: extend only the synthetic route's
qualified environment with exact Nix-store executable paths and SHA256 bytes
for Python, picotool, Git, Nix, nix-store, Docker CLI and the selected Task
launcher. Verify the union of their recursive Nix closures with the retained
SDK/compiler closure before admission. Bind closure metadata and dispatch
selection to the qualified environment and committed transitive source map.
Constrain this process and inherited workers to those immutable bin directories;
recheck every selected executable before mutations and worker admission. Missing,
non-store, changed or shadowed tools and incomplete closure receipts refuse.

Task is a selected launcher dependency, not proof of the already-running
ancestor's invocation. Explicitly select the local Docker Unix socket, refuse
foreign host/context overrides and bind that selection. The running Docker
daemon, Nix-store service, kernel, udev, filesystem and pre-Python launcher remain
trusted host boundaries; neither executable hashes nor closure verification
freeze their live state. Immutable archive/config/image ID checks remain required.
No credential contents are read. Preservation, deadlines, leases and recovery
are unchanged; old USB/register routes retain their policies. Empty registry
and all physical qualification gates remain mandatory.

Proof: focused tool-path/hash/closure/endpoint mutation and inherited-worker
fixtures, existing complete lifecycle tests, and a read-only committed-source
host receipt. No container, device, vendor or compiler execution is needed for
this software proof. A new qualification is required for the enlarged tuple.

## Register host dispatch binding (prospective)

UNVERIFIED implementation prerequisite for the first register episode: reuse
exactly the reviewed runtime primitives in `tools/forgix_synthetic_runtime.py`
(the filename is historical) rather than create a second dispatch/closure policy.
The register coordinator will select and activate the same seven Nix-store
executables before artifact/Git/image work, require the reviewed local Docker
endpoint and canonical complete reference graph, and bind the environment and
execution digests into the register qualification tuple and receipt. Keep its
empty registry and physical grade/clock/voltage/pin/loading gates.

Recheck full tool/archive bytes before register preservation, each picotool
operation, factory recovery and worker spawn/admission. Inherited register
workers retain the reviewed bounded PATH and endpoint and check the frozen
runtime at entry; transfer guards check dispatch selection without repeatedly
hashing binaries for each reply fragment. A register-specific guarded picotool
runner must be retained before possible storage failures. Preserve one operator,
existing deadlines, leases, cleanup/refusal and no-retry behavior.

Shared standalone USB policies, synthetic source/runtime implementation bytes,
firmware, compiled artifacts and physical checkboxes remain unchanged. Since
shared register backend source enters the synthetic execution map, that merged
source tuple must be freshly frozen later; this does not qualify either route.
Daemon/kernel/filesystem trust and selected-Task ancestor limits remain explicit.

Proof: `nix develop --command task forgix:spi-bridge:runtime:test`, existing
backend/coordinator/lifecycle and synthetic regressions, exact seven-tool/closure
mutation refusals and a real host-only inherited worker. A fresh read-only actual
committed register map and current immutable environment proof precede independent
review; no device, container producer, ARM/compiler/vendor build is needed.
Tasks1.1 and2.1–2.3 remain unchecked until their physical evidence passes.

The new register execution set includes the complete bridge build-source set
(derived from the build module's FILES) alongside transitive host helpers, the
runtime module, registry and protocols; its count is not an acceptance target.
The existing artifact guard requires every recorded build source still current.
Historical configuration003 includes older flake/Task bytes and cannot be promoted
to a current artifact by this runtime proof. Retain that refusal; a fresh separately
operated ARM build and independent artifact review precede future qualification.
No artifact-source allowlist or firmware/build policy is relaxed here.

## Prospective register qualification and finalization correction

Declared October 4, 2026 after independent source review of `69e22dff` and
before correction code. Preserve that author freeze and the independent failed
receipt (`96b09ffe2582ad92681ae5cf23bbf4656d5c1c2e1ce24fda04943646e0d0858a`).
The empty committed registry still blocks physical execution.

Bind the actual original board UID hash and preserved flash baseline hash in
the register registry tuple and independently require both exact valid hashes
in the physical qualification receipt. Every production/worker entry retains
the whole source/runtime and original preservation checks.

Use one 600-second acceptance clock through lifecycle, terminal persistence and
lease release. Lifecycle completion is provisional until finalization. Persist
a durable pending finalization record before release; only acknowledge normal
completion after release and terminal save/fsync return within the same clock.
Release, cancellation, storage and late-return failures preserve their primary
error, correct the authoritative session to failed where possible, and retain
or re-establish the conservative lease under the held global flock. A failed
corrective journal cannot turn the durable pending record or retained lease into
success. No CLI0 or physical acceptance follows such uncertainty.

Replay the original independent host probes and add missing/malformed/mutated
UID/baseline checks plus real temporary lease release, cancellation, deadline and
terminal/corrective storage failures. Preserve all failed attempts. Issue a new
immutable author freeze for independent review; fresh root configuration build
and artifact review remain mandatory. Shared standalone USB helpers, firmware,
FPGA candidates and qualification registries remain unchanged/unadmitted.

## Prospective shared pending-finalization refusal

Declared October 4, 2026 after independent review of `54bda122` and before this
correction. Preserve author receipt `664e7a3a`, independent failed receipt
`60300e84d14b1ac7b19e444b03ce875312ce34e8a07e265451b8bfedd7906420`
and the exact cross-route probe. The probe performs real temporary lease
release followed by failed active-lease recreation: only the durable register
finalization marker remains, and the synthetic operator lock wrongly admits.

Supersede the earlier shared-USB-unchanged restriction only for a common refusal
guard for `.scratch/forgix-spi-finalization-pending.json`. Presence of this
marker, including an unsafe/dangling symlink or malformed file, blocks Forgix
admission, access, dispatch and recovery. No marker parsing or generic override
can permit access. Use one shared predicate across root coordinators, standalone
USB run/recover, inherited lock checks, contained worker entry, serial/USB
identity selectors and preservation/picotool dispatch. Check before hardware
queries or opens and again at existing access/admission boundaries; keep owned
resource closure available. A matching synthetic recovery profile cannot bypass
this register pending state. Marker clearing stays solely in the already
reviewed register finalization path; this change adds no recovery/cleanup action.

Do not alter operation whitelists, firmware/flash/FPGA payloads, lifecycle stage
ordering, accepted historical USB/RF evidence, or physical qualification gates.
Replay the exact original cross-route probe unchanged and add actual temporary
lock/entry/refusal tests for each affected route, including marker appearance
during preflight and recovery. Run relevant USB, register and synthetic suites,
then freeze complete changed execution maps and current seven-tool/reference
closure proof. Historical freezes remain distinct; root must refresh all merged
production tuples before any physical action. No task acceptance or registry
entry is added.


Task3.2's [complete-profile boundary](../../../docs/research/forgix-clock-observer-protocol.md)
now identifies the distinct one-request RAM USB result path, direct B4 clock
binding, exact-image builder, dedicated ELF/startup policy, prefix-preserving
collector and bounded preserved measurement lifecycle. This is prospective
implementation scope; old registry/profile qualification is unchanged, and
neither host tests nor nominal clock assumptions satisfy physical inventory.
