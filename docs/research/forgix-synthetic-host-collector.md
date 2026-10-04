# Prospective finite synthetic host collector

UNVERIFIED host preparation for FPGA evaluation task 2.1. This document does
not admit loading, devices, FPGA timing, measured transport, or recovery. The
32 MHz setup failure in compiler episode003 remains a prerequisite failure.
The register collector/lifecycle and their qualification registry are unchanged.

The new caller-owned API binds the exact frozen stream contract at engine
contract initially frozen at commit `4a6077bbd9c182e830034da1a1920bcb990dd85f`
and its reviewed coherence correction `c4cae186`, protocol SHA256
`54c62ab91d77a5d7a9b8cfc62c78528de825c6d7bde7cb512c35724c5a675897`.
Its host parser accepts only 512-byte FSB1 DATA/CONFIG/START/END frames and the
three declared period/target pairs. Full nonce and RP/image hashes bind each
control; no auxiliary line protocol or address operation exists. CONFIG and
START are distinct 128-byte one-shot intents. START follows a successful exact
CONFIG receipt. An ambiguous write, partial frame, invalid CRC, clock reversal,
disk failure or identity/lock change aborts without retry or resynchronization.

The caller supplies an already-held inherited operator lock, selected original
identity, independently qualified synthetic lifecycle/artifact checks and an
absolute boot-based host deadline. Those checks run before opening and every
transport action. This module offers no hardware CLI, identity discovery, mode
change, load, configuration qualification or restoration. A caller must contain
possibly blocking open/read/write/close in an owned worker and independently
verify whole-group closure; the collector reports serial closure separately.
Injected host fixtures do not substitute for that qualification.

The CONFIG ceiling is min(boot+30 s, intent+20 s); START is before boot+30 s.
Successful finalization remains strictly before START+65 s. A failed deadline
path can use less than one second of STOP/snapshot grace and less than two
seconds of terminal drain. Host collection therefore ends by
min(boot+120 s, START intent+68 s); arriving bytes
never extend a ceiling. Every operation checks both pre- and post-return clocks.
The optional measured 100 ms host-reader pause occurs at START receipt+30 s,
with actual start/end retained. It is separate from any build-declared RP drain
pause or FPGA POP refusal. The caller must reserve lifecycle recovery time.

Create an exclusive private0700 directory with exclusive0600 raw/journal files.
Persist command intent before writing and every received chunk before parsing;
retain full raw bytes, including failed/partial prefixes and error-attached
consumed bytes, privately. Retain bounded operation timestamps, actual command
write counts and terminal failure type. No raw payload, device address, nonce,
identity or backup is published. Disk failure still reaches transport close and
is reported as incomplete persistence; bytes that could not be saved cannot be
claimed retained. A late fragment is saved but never accepted as timely evidence.

Strict lossless validation is fail-latched. A separate forensic ledger can retain
subsequent CRC-valid, correctly bound records after forward sequence gaps, with
exact missing ranges. Reordered/duplicate records, wrong tick/pattern/CRC or
conflicting controls stop parsing; never repair records. START establishes the
coherent64-bit FPGA anchor; record ticks must match anchor+(sequence+1)*period,
including tick32 wrap. END status0 requires target generated/popped/confirmed/
staged, no drops/refusals/pending/queued records, coherent done snapshot and exact
finite STOP tick. CDC API acceptance is compared with host bytes but does not
itself prove host receipt. END and independently verified closure are required
for a successful host collection; flash/factory recovery belongs to the caller.

Report source-record and pattern payload bytes separately from512-byte framing,
host per-second arrivals, actual arrival gaps, received sequence losses, reported
source/RP queue high-water, CDC partial/stall counters and reconciliation limits.
Per-second host arrivals include buffering and scheduler effects. They are not
calibrated clock measurements or independent electrical timing evidence.

Before integration, meaningful tests use the frozen real C engine's wire output,
independent literal controls, CRC mutations and preserved partial streams. Cover
all rates, wraps, failed snapshots, reported losses, ambiguous POP, partial/late
reads/writes, empty input, cancellation, disk failure, closure failure, identity/
lock refusal and measured host pause. The test recipe uses the locked Nix flake
and an owned private Taskfile; shared Taskfile/flake and hardware tasks stay
unchanged. Freeze all runtime source/contract/test inputs for peer review.
