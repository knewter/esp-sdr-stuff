# Prospective finite synthetic lifecycle

This separate production entrypoint is disabled by the empty committed
`tools/forgix_synthetic_qualifications.py`. Offline tests and compiler reports
cannot populate it. No FPGA transport, physical loading or RF acceptance follows.
The register route and its registry remain unchanged.

`nix develop --command python tools/run_forgix_synthetic_trial.py preflight`
requires explicit `--artifact`, `--binding`, `--baseline-a`, `--baseline-b`,
`--qualification`, `--private-dir` and loaded immutable `--image-id`. `run`
uses the same arguments; `--period` is exactly 2000000, 500000 or 250000,
with 960, 3840 or 7680 records. Host pause is fixed at 100 ms; RP pause is
bound to the compiled artifact. All files/logs/nonces/UIDs remain private.

Qualification covers the exact execution map excluding the registry, full
verified Nix environment, complete compiled artifact/startup/image tuple,
period/target and pause policies. Its digest and those tuple hashes form the
registry key. Committed registry bytes are frozen separately, without circular
hashing. Qualification requires measured grade, clock, SPI handoff, reviewed
whole loading/recovery and startup UID. Source or simulation proof is insufficient.

Under one inherited global operator lock, a shared durable lease precedes
any access. Any unresolved register/stream lease or unknown-closure marker blocks admission.
Initial preservation is potentially mutating. A 600-second acceptance clock
includes directory/lease/journal/terminal writes; work ends at 275 seconds,
reserving 325 seconds for factory return and two fresh full original reads plus
independent device comparison. Bounded container cleanup may extend outside an
operation deadline; such late results cannot qualify. No flash writing occurs.

The exact SRAM-only image is loaded through an owned immutable picotool
container. A conservative boot host epoch precedes load. One serial worker
selects topology3-3/PID4013, checked original 16-hex UID and a fresh unique tty,
retains all earliest bytes, and runs one CONFIG/START/END session. CONFIG/START
must finish within that conservative boot+30 seconds; the finite collector
uses boot+120 and START+68 failure bounds. Successful RP finalization stays
START+65; nominal FPGA and RP clocks remain distinct. Whole saved raw replay,
nonce/build/image/profile and lossless terminal/persistence/closure must pass.
Forensic loss accounting remains failed qualification.

Any possibly consumed preservation/load/configuration/START request requires
factory/full-original verification afterward. Unknown worker or container
closure prohibits further access, including recovery, and retains the lease.
A failed receipt or cancellation never permits retry/resynchronization. SIGINT
and SIGTERM are deferred during bounded recovery. Lease release requires saved
factory/full-original/whole-closure proof; crash or incomplete recovery leaves
an admission blocker. Independent physical-result review still precedes any
OpenSpec checkbox or accepted-ledger change.

## Explicit recovery follow-up (prospective)

Add a `recover` action for a retained failed session whose saved aggregate
closure is exactly true. It never reloads RAM or sends CONFIG/START. Require the
original durable lease, original saved private profile/execution/environment,
identical currently qualified tuple and full nonce, both original flash copies,
and the shared lock/unknown-marker checks. A fresh private output records one
bounded factory return and full original preservation under one 600-second
acceptance clock. Release the original lease only after durable factory/readback
and aggregate closure proof. Unknown/missing closure, missing/crashed receipt,
changed inputs/qualification/UID or a foreign lease refuse before device access.
A fresh qualification/review is required if executable inputs change. This
recovery action does not accept the failed transport or authorize a new trial.
