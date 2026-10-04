# Preserved Forgix register episode

Prospective protocol, October 4, 2026. Physical register readback remains
unverified. The committed qualification registry is empty: neither flags in
a receipt nor a CLI option admit an FPGA load.

The production coordinator selects the configuration-after-RAM-startup route.
An admitted profile must bind its actual ELF, manifest, embedded candidate,
firmware source, backend, coordinator and independent qualification receipt.
The receipt identifies board grade, clock, SPI handoff, startup UID and the
whole configuration/load/recovery review. Frozen execution includes the registry
and this protocol. The qualification receipt covers every execution input
except the registry, which is independently frozen from committed Git bytes.
This avoids the circular registry-hash/qualification-hash dependency.

Before device access, hold the shared exclusive operator lock, confirm no
unknown-resource marker or unresolved prior SPI lease, and durably create a
private session lease. Refuse changed inputs before each hardware stage and
serial transfer. Preserve the selected original device with two complete 2 MiB
reads, separate device verification and factory return; both reads must match
the original baseline. Preservation itself changes USB mode, so a failed
initial preservation also requires recovery when owned resource closure is known.

Then enter ROM, load only the bound SRAM ELF, wait for its UID-matching USB
bridge and permissions, configure the exact embedded image after startup,
verify matching image/source/nonce and unchanged enumeration, and collect the
bounded register episode. CDONE alone cannot prove image continuity. Retain
raw replies, configuration prefixes and durable intent/result events privately.
Register acceptance needs the correct source, counts/CRCs, scratch restoration,
FINISH, persistence and transport closure. Host fixtures are not these physical
measurements, and successful coordinator execution still needs independent
physical-result review.

Return to the original factory application and independently repeat full
flash preservation/verification. A successful final record requires both
resource closure and original-flash/factory verification. Release the durable
lease only after that proof. Process death, disk failure or incomplete recovery
retains it and blocks later operators, including the USB RAM CLI. The legacy
standalone preservation CLI is retired; its API remains inside guarded helpers.
An unresolved lease is not permission to delete it and retry: inspect its
private session and exact owned resources before a separately reviewed recovery.

The coordinator and lifecycle share one original 600-second acceptance clock;
initial receipt/journal persistence does not restart it. The lifecycle reserves
325 seconds for factory return, full verification and final checks. Existing
owned container/group cleanup can add approximately 42 seconds after an
operation timeout. This is a cooperative deadline, with OS responsiveness and
physical recovery separately qualified, not a strict wall-clock recovery bound.
Unknown closure prevents further hardware commands rather than guessed recovery.

Run host checks with:

```sh
nix develop .#ci --command task forgix:spi-bridge:coordinator:test
nix develop .#ci --command task forgix:spi-bridge:backend:test
nix develop .#ci --command task forgix:spi-bridge:lifecycle:test
```

`task forgix:spi-bridge:preflight -- --help` and
`task forgix:spi-bridge:trial -- --help` expose the required private profile,
binding, baseline copies, qualification and fresh output directory. Preflight
opens no hardware. With today's empty registry, both refuse a run profile
before artifact or device access. No bypass option exists.

Remaining physical gates: a matching Forgix attachment, actual board identity
and electrical/timing qualification, fresh preservation, configuration and
register readback, then several-rate synthetic FPGA transport with loss/backlog
and sustained-rate evidence. Nominal 32 MHz oscillator markings are not an
actual frequency/tolerance measurement. Its output reaches only the FPGA;
the RP controls oscillator enable and cannot read that clock directly through
the existing USB firmware. No inter-board wiring is assumed.

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
