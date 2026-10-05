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

## Staged synthetic finalization

The preserved temporary-file probes at `2ab2e7e` found late active-lease
release and post-unlink directory-sync failure followed by corrective storage
failure. Neither probe ran hardware or returned CLI0; both left an older
completed-looking session and no admission blocker. The correction stages
lifecycle facts as `synthetic_episode_observed` or `recovery_observed` and
durably creates the existing shared pending marker before lease release.
Marker cleanup requires the exact owned bytes, inode, private mode and single
link. Foreign or uncertain markers are never removed. All existing Forgix
admission, worker, preservation and recovery guards already refuse its presence.

The original operator FD close, lease release, terminal save/fsync, stdout,
post-output save/fsync and owned marker closure remain inside the original
600-second clock. Cancellation stays latched during bounded recovery; it cannot
qualify finalization. Failed finalization attempts retain the pending blocker
and active lease where possible, preserve the primary error and never promote
a staged record when corrective journaling fails. Unknown resource closure
still prohibits recovery. A failed transport with verified original restoration
and owned closure may close normally while its transport result remains failed.

Normal saved status is `pending_external_cli_exit`, with
`invocation_qualification=false`, `external_cli_exit_required=true` and a
separate `finalization_candidate_status`. Saved facts include the returned
operator-close, lease-release and terminal-output clocks. The process cannot
certify its future exit: independent result review must join matching saved
facts with an actually observed CLI0 within 600 seconds and explicit
postterminal shared-marker and active-lease absence. Saved status or stdout
alone never admits an episode. Recovery keeps its distinct candidate outcome;
it does not accept the earlier failed transport. Registries and physical
qualification requirements are unchanged.

Independent review `711b2203` preserves the first 56-group author PASS but
finds two additional boundaries: unknown closure plus failed shared-marker
creation, and cancellation ignored after stdout restored a prior SIGINT handler.
The follow-up establishes exact shared refusal while the original flock is
still held. Failed separate marker creation may use an exclusive link from the
already durable exact owned lease, with owned-inode/link validation. If neither
route establishes refusal for unknown closure, the owning process retains that
exact FD in quarantine. Acceptance is failed; there is no renewed timer, new
keeper service, hardware action, recovery or success. Cancellation stays latched
and does not release this quarantine; a qualified operator must establish known
closure before terminating its exact owner. Normal and known-closed failed
transport cleanup remain bounded. Prior signal handlers are restored only after
required terminal persistence and marker closure have returned.

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

Recovery atomically transfers the existing durable lease to the fresh recovery
output before access. The old saved terminal cannot admit another attempt after
that transfer. A crash before the new terminal, or unknown closure recorded in
it, blocks subsequent recovery even if unknown-marker persistence fails. The
old failure is never rewritten or accepted; recovery produces its own receipt.

The synthetic serial adapter accumulates individual POSIX pyserial `read(1)`
returns, attaching every returned prefix to a timeout, interruption or read
exception for private retention. Bulk `read(size)` can consume an internal
partial buffer and lose it on a subsequent syscall error; the old register
adapter remains unchanged. Real local PTY/EIO tests establish the distinction,
deadline retention and serial closure. This covers bytes returned by the driver;
unread kernel/device bytes and bytes lost below the syscall boundary remain
unobserved. The owned worker still bounds potentially blocking kernel calls.

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
