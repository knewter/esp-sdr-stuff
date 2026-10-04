# Finite synthetic lifecycle preparation

**Offline implementation; physical admission is disabled.** The separate
committed synthetic registry is empty. No device, vendor process or compiler
ran during this implementation/review. The register route and existing artifact
policies remain unchanged; no FPGA or RF task is accepted.

The new coordinator binds the original UID/full flash baseline, exact compiled
RP/image/profile, full nonce, committed execution inputs and verified Nix
runtime. One inherited-lock worker owns PID4013 CONFIG/START/DATA/END; another
contains saved-byte replay. A shared durable lease blocks register, USB and
stream routes after an incomplete session. One 600-second acceptance clock
includes receipt writes and reserves 325 seconds for factory/full-original
verification. Initial preservation is potentially mutating; failed/partial
load or stream operations recover after verified whole-resource closure.
Unknown closure prohibits further access and retains the lease.

Explicit `recover` uses the identical registered tuple and a known-closed
saved session. It atomically hands the lease to a fresh recovery output before
access, preventing an old receipt from bypassing a later crash or unknown
closure. It performs no RAM load or CONFIG/START: only factory return, two fresh
full original reads and separate device comparison. Failed stream evidence
remains failed. Missing closure/receipt, changed inputs or a foreign lease refuse.

The recovery freeze `2f101d3` passes **31 author and 11 independent groups**.
The final correction `a36f456` passes **35 author, 11 replayed independent and
7 new independent groups**, without skips. Historical proofs remain separate.

Author checks cover compiled-C wire frames, saved replay, strict UID/nonce/
profile/qualification bindings, real flock inheritance and lease-owner
exit/SIGKILL, blocked descendants, partial transport, cancellation, recovery,
late/storage failures and authoritative terminal receipts. Early review found
missing board/execution bindings, a cross-route lease gap, misleading fixture
labels and final lease durability/late-result issues; these were corrected
before the frozen run-path review. Separate recovery preparation followed.

A later actual POSIX test exposed a bulk-read prefix gap: pyserial consumed
11 bytes before EIO but returned none. The synthetic-only bytewise adapter now
exposes all 11 for private retention. Independent PTY tests cover interruption,
partial deadlines, late bytes, timeout setters and a full 512-byte read; the
collector saves and hashes the failed prefix after closing, without START or
retry. Unread kernel/device bytes and losses below the syscall boundary remain
unobserved; this is not physical throughput proof. The old register adapter is
unchanged. The reviewed 62-file fixture is an isolated source context; the
merged production execution/Nix tuple must be freshly frozen before
qualification. Deadline acceptance is not an unconditional wall-clock bound.

The existing 220,200-byte ARM001 artifact was read-only checked in its original
root context, including exact source/export/layout, embedded image/build/CRC
and recognized reset audit. This does not establish a whole boot path, physical
clock/grade/voltage/pin ownership, timing, loading, throughput or recovery.
Independent physical-result review remains necessary. See the exact hashes and
review scopes in [checks](checks.json) and the
[prospective lifecycle contract](../../research/forgix-synthetic-lifecycle.md).
