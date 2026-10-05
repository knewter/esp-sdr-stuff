## Context

See [proposal](proposal.md) for the problem and scope. The hardware identity is recorded separately from untested reception and transport behavior.

## Goals / Non-Goals

**Goals:** Decide which interference, educational DSP and short-burst applications are useful on this board.

**Non-Goals:** No whole-session Bluetooth capture, guaranteed packet logging, continuous audio or encrypted-content access.

## Decisions

Make spectrum observation the first application. A 16,380-sample window is roughly 0.205/0.410/1.024 ms at 80/40/16 MS/s; choose waveforms only after duration and bandwidth fit are checked. Offline decoding of a captured burst is distinct from reliable live reception.

The host records revisions/settings/results; firmware owns modem and memory access; an FPGA, if selected, owns only its explicitly measured transport/processing boundary.

## Risks / Trade-offs

Packet timing, frequency hopping and transfer gaps can dominate detection. Failed decoding may reflect truncated data rather than bad demodulation.

## Validation and decision

At least 100 deliberately emitted repeat events with ground-truth counts and capture hit rate; a decoding claim includes a complete waveform and verified payload.

Physical proof: 100 counted emissions plus capture timestamps and a saved waveform; offline proof: run the selected decoder on the pinned capture and compare output to the known payload. No decoder or protocol support is assumed in advance.

The [counted-trial protocol](docs/research/ble-counted-trials.md) predeclares three 255-event repetitions using a single-channel legacy source and an actually observed controller termination counter, independently of ESP decoding. It requires full waveform replay, exact known data and explicit unresolved outcome bounds. Controller-reported completed events must remain distinct from independently measured radiated RF emissions.

[Three source-only diagnostics](docs/evidence/ble-counted-source-smoke/README.md) accepted parameters, data and finite enable commands but produced no termination count. They are not receiver trials and close neither event-observation task. The source counter must pass before the predeclared receiver trials run; no guessed event-mask overwrite or arithmetic interval-derived denominator is allowed.

## Visual plan

[Experiment flow and provenance](docs/design/the-receiver-can-observe-and-decode-short-bursts/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.

## Timer diagnostic boundary

Subsequent [timer diagnostics](docs/evidence/ble-duration-source-diagnostics/README.md)
observe `0x3C` termination with completed count zero; the [prospective RF
discriminator](docs/evidence/ble-zero-counter-rf/README.md) is inconclusive.
These diagnostic captures are separate from the three counted receiver trials.
Original counting and acceptance criteria remain unchanged. A recorded usable
source denominator is still required.

The [bounded register observation](docs/evidence/receiver-register-observation-002/README.md)
completes 20 valid snapshots and 81 ordered sampled stages with full original
restoration. Selector 48 / bit23=1 throughout narrows a sampled configuration-field
mismatch explanation for that run; it does not decode a packet, qualify source
counts or explain the fresh SDR nulls. The first supervisor failure is retained.
Trial B remains withheld until its original fresh SDR-positive prerequisite.

The [matched ten-bit controls](docs/evidence/ble-matched-gain-001/README.md)
now reproduce one fresh manual48 owned packet with independently verified
protected CRC, whole AD and complete waveform window. All 1,994 inputs and both
full restorations pass [independent replay](docs/evidence/ble-matched-gain-independent-review/README.md).
Hardware gain retains zero owned and one redacted foreign CRC packet. The source
remains uncounted, three-response proof remains incomplete, and this profile
does not replace Trial B's original eight-bit/BW12/hardware-gain prerequisite.

## Extended primary-header preparation

The [reviewed primary preparation](docs/evidence/ble-primary-preparation/README.md)
adds a separate zero-data source profile and strict CRC-valid extended primary
header parser. Eighty-nine scoped host checks pass after a peer-reviewed
auxiliary-offset timing correction. This is preparation, not new reception.
Missing AdvA, ADI-only identification and auxiliary AD cannot establish ownership.
Zero data does not force a particular primary layout or AUX omission.

Controller-completed extended events remain distinct from independently counted
primary RF transmissions, including permitted event/PDU omission. Those historical
monitor records omit some requested HCI fields; do not claim their independent
physical verification. Original emitted-count, full waveform, three-response
and Trial B prerequisites remain unchanged; no task is checked by these tests.

## Reviewed implementation prerequisites

The [failure-retention review](docs/evidence/capture-failure-retention/README.md) verifies private UART prefixes, uncertain START closure and unchanged successful CSV bytes. Caller integration passes independently. The earlier failed fragment remains unavailable. The final original BW12 trial requires a fresh runtime/device freeze and full preservation/restoration; this source preparation supplies no reception or air denominator.

## Final original ladder outcome

The [final original BW12 control](docs/evidence/ble-bluez-control-007/README.md) completes the prospective ladder: all 1,151 captures, whole decoder/scalar replay, source schedule, cleanup and full restoration pass independent audit. Zero CRC-valid packets and no repeated owned-source nominal-band rise supply no emitted-event denominator or detection/miss rate. Original Trial B remains withheld; neither radio acceptance gate is relaxed.

## Separate offline precision diagnostic

The [prospective same-waveform protocol](docs/research/ble-same-waveform-precision-protocol.md)
compares all246 historical and1010 matched-manual ten-bit waveforms with their
exact upper-eight-bit transformations using unchanged blind decoder bounds.
This diagnostic supplies no new RF capture or emitted denominator and changes
no physical acceptance gate or accepted requirement. Earlier outcomes remain.

## Conditional zero-data primary-source readiness

The [separate prospective readiness protocol](docs/research/ble-primary-zero-data-readiness-protocol.md)
qualifies one exact zero-data extended-source controller profile/count100 and
complete monitoring/cleanup before any future receiver condition. It verifies
all independently sanitized v1 HCI fields and retained ownership/deadline proof.
Controller events remain distinct from emitted primary PDUs; previous failures,
original legacyTrialB/count/RF gates and accepted specs stay unchanged. A future
three-repeat ten-bit/BW20/manual48 receiver trial is conditional and separately
frozen; this appendix admits no source action or receiver.

## Corrected source-only preflight proof

The [readiness preparation](docs/evidence/ble-primary-zero-data-readiness-preparation/README.md)
now passes 104 author and five independent groups after rejecting late intent/lock
and spawn returns, and force-cleaned descendants incorrectly counted as natural
completion. Exact source/runtime/import and owned-group checks are retained;
old failures remain failed. Physical profile qualification still needs a fresh
root binding/freeze and one separately operated source trial. No receiver,
radiated-primary denominator, original Trial B or accepted requirement is admitted.

## Independently reviewed source-only outcome

The [saved zero-data source001 audit](docs/evidence/ble-primary-zero-data-source-001-review/README.md)
passes the exact requested controller profile: 23 native / 11 monitor records,
five ACK0 pairs, empty host advertising data and matching `0x43/count100`.
Selected power 7 dBm is an uncalibrated controller response. Natural group
completion and unchanged controller state are recorded operator/code attestations;
child PGIDs/container IDs and exact closure brackets were not retained. The
corrected root preparation passes 107 author plus five general and three
actual-Git peer groups. Earlier failures remain retained.

This qualifies the separate source profile for prospective receiver preparation,
not radiated primary count, reception, original Trial B or tasks 1.1/1.2.
A separately frozen and independently reviewed ten-bit/BW20/manual48 condition
with three ON/OFF pairs is next. Preserve the low snapshot duty factor and
unknown primary emissions as limits on any null result.

## Conditional three-repeat extended-primary receiver preparation

The [prospective bounded receiver protocol](docs/research/ble-primary-receiver-three-repeat-protocol.md)
fixes ten-bit/16MSPS/16380-pair LO2401/BW20/manual48 captures and three independently
monitored zero-data source instances after independently reviewed source-only
qualification. It preserves full flash/boot recovery, private failure prefixes,
all repetitions and actual OFF/ON timing. Controller completed events remain
distinct from radiated primary PDUs; complete CRC+present private AdvA and whole
guarded acquisition brackets are required before source-associated RF claims.
This is implementation preparation; no physical checkbox or accepted requirement
changes, original TrialB/count/reciprocal-response gates and previous outcomes
remain unchanged. Proof is frozen offline caller tests and independent preflight
before a sole-root-operated receiver condition.

## Separate timed-v2 opportunity extension

The [prospective timed-v2 protocol](docs/research/ble-primary-timed-zero-data-v2-protocol.md)
responds to the reviewed fixed365null condition's11 guarded ON windows without
changing precision, receiver settings, placement or decoder search. Request
handle1/map37/LE1M/20ms/emptyAD with Duration25000ms and MaxEvents0. Require a
separately qualified actual0x3c timer termination and complete controller/monitor
profile/cleanup; actual UINT8 completed-count metadata agrees across readers
but cannot supply a denominator. Existing v1 duration/count/unlimited validators
and counted-success gate explicitly reject these arguments and remain unchanged.

A separate native runner/container helper and source-bearing tagged Nix archive
own the new behavior, reusing unchanged v1 low-level primitives without modifying
module globals. Old source/image derivations, monitor/parser, decoder and old15
receiver/holder inputs retain their exact reviewed bytes. A NEW private caller/
support/dispatch/account/holder owns the v2 qualification schema and scheduling;
all actual transitive helpers, runtime/archive and loaded identities receive
fresh independent freeze proof. New flake/Task inputs require refreshing other
production tuples and any later strict19-source register artifact; no guard is
weakened and no existing artifact is relabelled current.

One unchanged continuous180-second receiver contains three25-second ON episodes.
Each45-second episode clock begins before controller/freeze/intent/admission/
spawn work and ends after natural owned closure and durable verification.
Baseline10 + three inclusive45 + two OFF2 + final OFF10.1 totals159.1 seconds;
source3 must close before ready+165 and the last intact payload must extend
strictly beyond10 seconds after that closure. Existing monitor240/260/275 and
whole acquisition420 ceilings remain. All helper timeouts fit the remaining
minimum clock; preflight overhead cannot escape the episode budget.

The measurable diagnostic coverage gate is100 whole guarded ON brackets total
and25 per repetition. At historical delivery the requested75 enabled seconds
could yield about150 windows before guards; this is an estimate, not RF proof.
Independent whole source/waveform/restoration review is required for any narrow
positive or null report. This diagnostic cannot close original emission/hit-rate
tasks, the three reciprocal-response requirement or original Trial B. Planning
admits no implementation, container/package build, source or receiver action.

## Reviewed timed-source implementation and archive

The [current software and archive proof](docs/evidence/ble-primary-timed-source-host-preparation/README.md) completes tasks 4.1/4.2 after retained reporting, resource-access and deadline corrections. Source, image, whole runtime contents and refreshed Forgix production inputs pass independent review. Caller admission, actual source-only qualification and the new receiver/holder remain separate prerequisites; no physical acceptance gate or accepted requirement changes.

## Source004 bounded verification prerequisite

NEW private source004 preserves source003 and its outer launcher. Its controlled
child configuration/environment excludes ambient Nix configuration/plugins
before the pinned bootstrap starts; the parent environment remains separately
frozen. One pure locked-current-revision selection before monitor may retrieve
only exact locked public source inputs within165/300 seconds, without registry,
lock update, arbitrary provider or output build. Root must prove the actual
CLI configuration, selected provider and current source/runtime equivalence.
Pure evaluation alone did not prove the earlier draft's no-fetch promise:
a cache-write error can enter Nix's remote accessor. Preserve that rejected
draft; bounded authorized retrieval before monitor explicitly replaces its
new promise, not an original RF/content/deadline requirement.

After readiness there is no selector/eval/fetch/realise/build. Every current
byte, alias, revision, environment/import, complete local reference graph and
NAR content, and both entire archive proofs remain fresh under45 seconds.
Up to four disjoint whole-path NAR workers and two whole-archive workers retain
exact union, job/input identity and full result equality. Each group has its
own owner; a bounded manager never shares one mutable sequential worker owner.
Durable pending and a live independent inherited-lock keeper precede the FIRST
worker. NEW inner and outer gates require the complete verifier ledger, natural
whole-group absence, closed FDs, bounded results/logs and timely durable terminal
data. Partial spawn, missing results, forced/unknown closure, cancellation and
storage failure cannot release qualification or become success.

Caller30/native32/source45/whole165/outer300 remain unchanged, including all
frontwork, close and persistence checks. Removing14.289 seconds of selection
alone leaves22.826 seconds, still too slow. Sharding estimates prove no speedup;
host load/shared storage remain limits. Harmless process/flock, graph/archive,
config/alias and terminal-failure tests plus independent review must precede
root-only current full verification/frontwork timing. No skipping, cached
content PASS, deadline renewal, automatic retry or physical acceptance follows.

Private design003 SHA256 `65ac83686848b49896ca1f6d169d81162027f4106a9383c3d436c748be1b9976`
and controlling scope `43e9ed62566eb313a197ce8e7b09a75fe0c0da408482d21cea9e1bfd7dace239`
are independently reviewed by receipt
`eda93ed36c0e31d8c2bc7526cb54b219bfc6d0ddfbd3d5b0a7e4c5060f61f6db`.
This pins prospective architecture only; actual004 implementation, CLI/current
tuple, timing fit, controller qualification and receiver operation remain open.

## Source004 cost attribution before optimization (UNVERIFIED)

This host-only prerequisite refines task4.3; it changes no controller wire,
original ESP32 receiver settings, native runner, RF or FPGA behavior. No S3/C5
capability is inferred. Historical whole preparation and prospective timed
admission have different scopes: source45 was not run in the accepted read-only
sample linked in the proposal.

### Baselines and measured limits

Saved-only timing report SHA256
`d25cc545a6abe87ad85828c97ae1b2e2db045591715a09d4793d9331ee256a12`
binds19 subject files and the analysis script at historical revision
`2ab2e7e82b5394b95b4968e191a7d665d1203de9`. Its75.134332621-second
first-verifier-intent to phase-descriptor-return interval partitions exactly:

| Saved ledger interval | Seconds |
| --- | ---: |
| Before six content-worker intents | 31.930573154 |
| First content intent to last saved content output | 30.320420938 |
| Last content output to final Git intent | 0.112357234 |
| Final Git intent to saved output | 0.829050940 |
| Final output to phase descriptor return | 11.941930355 |

The35 sequential Git intent-to-saved intervals total25.632887186 seconds;
their actual Popen call brackets total0.082496289. Neither number measures Git
CPU alone. Six workers' group-absence times are assigned after the pool drains,
so they cannot rank individual worker costs. The descriptor-close call itself
took0.000273236 seconds; the11.941930355-second remainder includes ledger,
seal and validation. Another15.744415622 seconds elapses from phase descriptor
return to root FD-close request, including later persistence and terminal
revalidation. These brackets do not isolate fsync, hashing, parser or kernel I/O.

Static code counts, not elapsed measurements, show256 durable/output writes
and at least512 file/directory fsync calls in the42-job phase; six workers repeat
274401536 executable-hash bytes. Each archive has three same-phase compressed
reads. `Manager.check` checks deadlines and retained keeper identity; it does
not enumerate all `/proc`. Whole process scans occur in group qualification,
member checks and per-job seal/terminal validation. Their costs need measurement.
The observed30.320421-second content span already exceeds13; removing sequential
Git and sealing costs alone cannot prove fit. Forgix's different268-path proof
and13.244-second sample cannot substitute for this305-path source tuple.

Corrected source004003 is the implementation baseline, not a timed admission:
author revision `ffdaf7649680ef25346bd1fcd46df661d5990735`, immutable47-file
bundle,143 author and24 independent groups with zero skips, independent receipt
SHA256 `5a130351abbba631f51db4a3d7a246cdf16f1fe9e69160fbd5bd9a57afe86773`.
This privately retained saved review covers complete preparation and producer
cancellation. It does not supply actual current-root equivalence or source45
timing. Preserve its fresh pidfd/member qualification before each individual
signal, common clipped cleanup budget, reaping, descriptor uncertainty and
keeper/pending quarantine. Existing manager-worker cleanup receives no broader
claim by citing producer tests. Retain002/003 bundles and failed evidence exact;
instrumentation creates a separately identified bundle with its entire expanded
source map, never a relabelled old receipt.

### First implementation scope: bounded measurement only

Add a private bounded event stream with monotonic request/return brackets,
operation identifiers, bytes/counts and successful/failed outcome. Measure
worker CLI and parser/hash boundaries, executable checks, process census,
each existing fsync call and ledger/output persistence and final validation.
Record individual body-completion timestamps inside each worker payload, before
serialization, separately from parent result receipt, group absence and terminal
observation; a payload timestamp is not an operating-system process-exit time.
Reconcile exact job/result counts and
graph/shard/archive request hashes; overlapping durations are not additive.
Retain raw ledgers and event bytes in the immutable proof, and emit only
sanitized aggregates publicly. Record wall and CPU where available with their
scope, without claiming they isolate shared-storage or scheduling causes.
Use opaque operation identifiers and bounded numeric/hash fields rather than
raw environment, command arguments, controller bindings or device identities.
Bind dynamic timings to a NEW per-phase ledger or sidecar receipt and its exact
source/request/result hashes. Keep them outside deterministic frozen tuple
fields compared by fresh snapshot equality: matching content does not imply
equal durations, and timing variability must not create false content refusal.
Missing or invalid diagnostic proof still denies measurement completeness;
measurement success never supplies content or operational PASS by itself.

No event may suppress or move a predicate or deadline check. Instrumentation
and its persistence remain charged to the original clocks. Bound event/output
sizes before spawning; missing, duplicate, overflowed, partial, changed or late
records retain failure and deny measurement completeness/admission. Measure
existing durability operations without adding a separate fsync per event. Use the
existing durable pending/keeper and owned terminal path; logging faults must
not leak children, close an uncertain reused FD or release qualification.
Harmless saved/host fixtures first verify event conservation and cancellation
under injected clocks and storage faults. Preserve143 baseline groups, actual
inherited local flock and owned descendant fixtures, plus independent review.
No actual store, daemon, compiler, controller or device operation belongs to
this author implementation phase.

Then the sole root operator freezes the actual current source/runtime tuple
and performs one bounded read-only complete verification.
Use the existing read-only preparation's165/300 scope and explicitly report
that no source45 clock or monitor was started. A completed read-only measurement
may retain costs exceeding13/45 and must report timed-admission refusal; it
cannot renew, start late or replace a future actual source45 clock. All costs
remain charged to their original invoked phase and durable terminal scope.
Preserve all14 roots,
305 NARs and1220 edges of the baseline (with any actual expanded closure fully
enumerated),22 project inputs, every actual import, the whole private bundle
and binding, every selected tool identity, and both entire archives. Four disjoint
NAR shards and two archive workers keep exact union and at most six workers.
The original historical map has45 private files; corrected003 has47. Future
instrumentation additions must be included rather than forcing either old
count or dropping inputs. Repeat samples for variance require a separately
declared bounded root experiment; no implicit retry is authorized by this plan.

### Conditional alternatives after attribution

- An owned bounded committed-blob batch could remove separate Git-job overhead.
  It must return every revision/path/length/hash/body record, preserve initial
  and final HEAD/clean/flake checks and fresh local rechecks for all project and
  imported bytes, and refuse omitted, duplicate, reordered or partial records.
  Reuse of immutable blobs is limited to that one fresh snapshot. Its protocol
  inventory and ownership need a separate reviewed update before implementation.
- One fresh process census indexed across all owned groups could remove repeated
  scans within one observation. Keep retained PID/start-time/PGID/SID/pidfd and
  member history, unknown-descendant refusal after leader exit, fresh complete
  seal/terminal scans and fresh identity qualification immediately before any
  signal. No cached-empty, leader-only or time-throttled ownership substitute.
- Same-boundary canonical executable hash reuse could remove duplicate role
  reads while retaining invocation-alias checks and all pre/post byte gates.
  A compressed-byte hashing reader could combine a whole archive hash with its
  complete parser pass only if EOF/trailer/trailing bytes, config, layer diffIDs,
  source/native/v1 bytes, labels, overlays, links and unsafe/duplicate paths
  receive equivalent checks. Differential malformed-archive proof is required.
- Different scheduling of the same four balanced NAR shards and two full archive
  workers is a later hypothesis. Retain maximum concurrency and conservation;
  measured shared-storage contention, not shard sizes alone, selects it.

These alternatives are deferred decisions, not the first implementation scope.
After measurement choose the smallest justified change and revise this plan
before code. A measured negative feasibility result is valid; no compatible
partial proof, cached content PASS, manifest-only parse, smaller closure or
raised clock follows.

### Fit and promotion gate

Source45 includes every post-ready controller/freeze/image/intent/wrapper/native
parameter and data-ACK step, natural close and durable result. Native ENABLE
requires32 seconds remaining, leaving at most13 for all preceding frontwork;
caller30 is a separate, weaker pre-spawn floor. Preserve13/45/30/32/165/300,
monitor startup75/active80, all clipping and original failure retention. Full
fresh read-only timing must show credible margin for the remaining frontwork;
a verifier below13 alone is insufficient. Root current complete proof and
independent saved whole review precede a separately frozen actual source-only
qualification. Neither measurement completeness nor reduced latency closes
task4.3's physical part, task4.4, any receiver task or accepted RF requirement.

## Timed receiver owned cleanup prerequisite (UNVERIFIED)

This refines4.4 in a distinct NEW ignored bundle. Preserve receiver001–004,
their failures, exact old15 inputs, frozen v1/native source, firmware/settings,
main helpers, full4MiB backups and source qualification provenance. The active
caller subclass inherits receiver004 `Child.fail_close`; the independent probe
executes that exact boundary, with signal operations captured rather than
performed. Original base source SHA256
`80da053cdefc7f54389a3caf27aaf22c890fe0371b34715bedbd8ae2f86aaee1`
and caller SHA256
`a30f2e4f822764d37d8e2c3d02bc4e4d96c083ce868402b866911584c9243584`
stay unchanged. The probe does not execute Child.start or attest an actual
numeric PID reuse. Independent minimum requirements are pinned by SHA256
`d07ffc6904fc34411874396a71e0ebd38576bc293d0b252d2586cefa4fc68ca8`.

### Original authority and complete member closure

Retain original spawn PID/PGID/SID/start ticks/boot identity and individual
pidfds privately, separately from mutable public receipts. Preserve authority
after partial spawn, deferred-entry cancellation and failed identity/log writes.
Qualify every intended member freshly before an individual pidfd signal; a
leader does not establish group ownership. No numeric PID/PGID signal follows
missing/mutated identity, a reaped leader or uncertain membership. Retain member
history so disappeared leaders, escaped/late/unseen descendants and modeled
numeric reuse cannot become leader-only absence proof. Ambiguous members receive
no signal and closure remains unknown; do not invent a new guardian or broaden
ownership policy to make the fixture pass.

### One declared cleanup clock, separate restoration scope

At the first failed-child cleanup or aggregate source/monitor/UART worker teardown,
set the shared cleanup deadline once to the minimum of the original caller
deadline, that entry plus30 seconds, and holder first-cancellation plus1800
seconds when present. Pass that exact absolute deadline to all children; charge
identity/membership, TERM/KILL, reap, log flush/fsync/close, receipt and descriptor
effects for those workers and their members before and after. Later children, new membership and repeated signals
cannot renew it. Normal completion of sequential source episodes remains under
its original source45 and role bounds and does not start this aggregate clock.
An expired/failed teardown cannot count as natural completion and must retain
unknown-owner quarantine rather than release the operator or access an endpoint.

Preserve source45/native32 reserve, receiver readiness30/acquisition180,
monitor readiness15/capture240/whole260, acquisition420, receiver caller5400 and
holder5400/first-cancel1800. Prior source qualification whole300 is distinct.
The new30-second process-cleanup scope does not shorten or renew full physical
restoration/holder finalization: those remain under the original5400/1800
ceilings after positively verified process/controller closure. Unknown UART,
process or container ownership blocks restoration and endpoint actions.

The30-second target set excludes the lifecycle caller/holder coordinators and
the keeper that retain the operator during restoration. Those processes, their
own descriptors/receipts and their actual terminal join remain under the original
5400/first-cancel1800 scope. No new30-second clock starts after restoration and
no coordinator is forcibly killed under this shorter worker deadline during
unresolved UART restoration. Holder forwarding and coordinator cleanup still
require original member/pidfd authority under their original absolute bounds.
Ordinarily reaped exit0 members with complete retained history may establish
natural closure; a reaped leader with lost/ambiguous complete membership cannot.

### Complete caller and holder handoff

Apply authority to all source, monitor and UART roles and holder forwarding/
forced cleanup, including failure before identity persistence. Preserve exact
CID/name/image matching and both ID/name absence checks. Source disable/remove
ACK0 and socket OFF may prove a bounded cleanup fact, not timed qualification,
air count or natural process success. Natural completion requires actual exit0,
complete owned-member absence, durable logs and closed descriptors within the
original bounds; forced cleanup remains failed. Clear disposable FD references
before uncertain close, never retry a consumed number, and retain conservative
failure authority without closing a replacement file.

Review holder admission/spawn/cancellation, caller finally/restoration decisions,
keeper release, original parent-FD acknowledgment, private/shared marker closure,
terminal persistence and cancellation-handler/latch effects as one chain. Saved
completed-looking bytes cannot qualify a late/failed terminal effect. Keep the
existing keeper/pending/quarantine refusal and require actual external CLI exit
plus the complete ownership handoff; no new keeper release policy is authorized
by this plan. Operating-system/filesystem responsiveness remains a trusted host
boundary, not something a cooperative deadline or fixture establishes.

### Proof and promotion

Retain the literal five-case failing probe unchanged. Add separately frozen
corrected controls and real own-session/descendant, actual reap, escaped/late
member, mocked numeric reuse/signal, partial-spawn, identity mutation, FD reuse/
ambiguous close, deadline/cancellation, every-role, pending/keeper and actual
subprocess normal/recovery/failure cases. Replay every original receiver004 test
and unchanged historical helper; complete source/import/runtime/archive maps
cover the whole new caller/holder path. Author tests use pinned Nix-declared
tools and private Task commands, with no actual service, store, compiler,
controller or device operation. Freeze source, commands, logs and actual exits
for independent whole-chain review before root transfer.

Root copies and rehashes the new whole private bundle separately, preserving
every prior receipt. Missing actual source4.3 qualification still refuses the
operational receiver freeze before archive/runtime queries or device access;
no dummy qualification may replace it. Host handoff alone closes no4.4/4.5
physical dependency. Fresh actual source/runtime/archive/import proof, the
historical921600 artifact/settings, full preservation and sole-root admission
still precede one separately frozen condition; no automatic retry or new RF gate.


## Exact provider preparation and one NEW cost follow-up (UNVERIFIED)

This small planning refinement preserves tasks5.1–5.5, including checked host
preparation5.1–5.3 and open measurement/attribution5.4/5.5 at3dc0eaf.
The host owns dependency preparation and cost measurement; no firmware, RF,
transport, FPGA or native producer behavior changes. Root cost003 at revision
948af8c3129d338c96afbe623a7f421dc3091e93 ended Task201/prepare2 after6.276427457
seconds externally observed. Six selection jobs returned actual0 and naturally
closed: Git revision/clean, committed flake.nix/flake.lock, bootstrap effective
config and pure provider selection. Selection returned the exact qfwk7cy provider
output below, but its filesystem-presence predicate refused before the seventh
provider-config job. Full NAR/archive verification/cost measurement did not start.
This failed prefix is not a complete event/clock reconciliation or a speedup.

Preserve all43 manifest-named output bytes, selection requests/results/costs,
ownership/FD ledgers, failed/pending markers and original actual Task log; retain
all four root start/terminal/transfer/failure receipts and every previous cost
failure. The failure-manifest SHA256 is
`1f572b584f5bb3f34b2ad53a9d96c0b510ee88c3411903c297dd4c58c91eac16`;
actual external terminal receipt SHA256 is
`978b4151064e9891e1df60b24a5d72af058b2040367648a015fc2a0c2db5e3ba`.
The missing selected provider was
`/nix/store/qfwk7cyvb885l2mc06ac3a7nmv19nigi-nix-2.34.8`, derived from the locked
flake input's `legacyPackages.x86_64-linux.nix`. The preserved bootstrap
`/nix/store/3vd56d4l3ih231ci008zyvrjjs199zz5-nix-2.34.8/bin/nix` with SHA256
`05c4fbc073d68c5d09f5254eebb3fd92594a5f1c10bd9e01a50c6136a76caee4`
is distinct. Equal version strings, arbitrary system Nix, copied binaries or a
symlink alias cannot satisfy exact selected-output identity. No GC deletion
cause is inferred from the saved absence alone.

### Recovery is separate from dependency preparation

The failed attempt's keeper/quarantine recovery is owned by the independent
reviewer and sole operator. This planning author does not query live processes,
clear pending markers, release a lock or reconstruct a member ledger. Before
new operation admission, require the independently reviewed qualified recovery
receipt joining original process/member/pidfd authority, actual closure, original
FD/keeper handoff and terminal effects under the existing recovery policy. Saved
selection closure does not establish keeper/whole-attempt recovery. Retain its
failure and qualified-recovery records separately; do not relabel the failed
measurement as successful or change existing keeper release policy. Unknown
authority continues refusal. No dependency or follow-up Task may implicitly
perform recovery, controller queries, restoration or a producer action.

### Exact provisioning outside every measurement clock

Implement a small reviewed Task entrypoint, proposed name
`source004:provider:retain`, bound to the current committed flake.nix/flake.lock,
exact explicit Git revision and pinned bootstrap. Its pure expression selects
only `f.inputs.nixpkgs.legacyPackages.x86_64-linux.nix` from
`builtins.getFlake` at that immutable local Git revision. Use explicit no-update/
no-write-lock flags and no registry/ambient package/channel/override fallback.
Capture the full argv/expression/config, locked inputs, source/output/derivation
identity, actual terminal, retrieval/build logs and executable hashes. Provision
only that exact derivation/output through the locked flake; any permitted exact
public substitution or build is a declared dependency operation outside the
read-only measurement. It is not source optimization or measurement work.

Use a persistent private ignored out-link, for example
`.vendor/source004-nix-roots/<locked-tuple-digest>/provider`, with Nix's registered
indirect GC-root mechanism. The reviewed Task must verify root registration,
exact output target and retained runtime closure, not just create an arbitrary
symlink. Retain it through measurement and independent review; exclude it from
scratch/worktree/Task cleanup and do not overwrite a root for another tuple.
Record source/input roots needed for the frozen selected tuple separately where
required. A scoped provisioning recipe may use `nix build --expr <frozen exact
expression> --out-link <persistent path>` with an explicitly reviewed provisioning
policy; actual support and successful root registration need receipts. Nothing
is globally installed or changed in host Nix configuration. No provider guard
is relaxed and no realization is inserted into selection/verification.

The measurement's existing controlled configuration still forbids output
realization/build and preserves its explicit store URI, plugins/registries/
builders/substituters policy, selected-provider checks and all original content
predicates. Provisioning has separate declared settings and artifacts; its
outputs cannot serve as cached NAR/reference/archive/content-validation results.
A retained provider is available input, not fresh proof or admission. Future
missing/changed root/provider/config refuses instead of fetching/building inside
the timed measurement or silently choosing bootstrap3vd.

### Independent provisioning review and current-tuple rebind

After qualified recovery, dependency provisioning and its saved review, freeze
a NEW complete source/current-map binding at the actual committed revision.
Preserve all original62 private/22 project transfer subjects and their historical
tests/failures; add any Task/provision helper/import/flake/source changes to the
whole union explicitly, with no dropped roots or old artifact mutation. Compare
producer/native/v1/receiver/firmware bytes and original clocks/ownership/content
fields unchanged. A Task/helper addition changes a project tuple and requires
the corresponding reviewed complete archive/import/tool/map rebinding; it is
not permission to reuse948 as current. If the selected provider changes because
of a separately reviewed locked-input change, retain qfwk7cy failure and review
the new exact tuple rather than claiming qfwk7cy was restored. This plan authorizes
no lock/input change; the expected provider remains exact qfwk7cy under the same
locked derivation. Require independent source-bound readiness and whole current
byte/map comparison before a sole-root new declaration.

### At most one separately declared root read-only follow-up

Only after the above reviews may the sole root operator declare one NEW bounded
whole cost follow-up with new output/start/terminal/failure paths and an exact
command/tuple/readiness receipt. It is not a resume of cost003, an automatic retry
or a child task of provisioning. The inner165 and outer300 clocks remain original
absolute scopes for that new experiment, with no pause/reset/per-worker renewal.
Run the reviewed root:prepare read-only entrypoint, retaining fresh local content,
all references/NARs/imports/tools and both full archives, complete worker/keeper/
FD/terminal ledgers, reconciled cost events and actual external CLI. Keep original
complete baseline305/1220/14 proof or its honest expanded whole closure, not a
partial compatible subset. All setup that belongs to the measurement remains
charged; only the separately declared dependency provisioning occurs outside it.

No monitor/source/controller/daemon-image/device query or producer is started;
no source45/native32 floor,13-second frontwork gate, caller30 or physical
qualification rule changes. A complete result can support saved cost analysis
and a fit/refusal recommendation in5.5. It cannot by itself qualify source4.3,
admit a receiver, promote6.x ownership architecture, close4.4–4.6 or original
TrialB/count/reciprocal-response gates. A failed, partial, late or ownership-unknown
follow-up remains failed with its full prefix; no second automatic follow-up.

Official Nix references describe [build/out-link behavior](https://nix.dev/manual/nix/2.34/command-ref/new-cli/nix3-build)
and [GC-root semantics](https://nix.dev/manual/nix/2.34/package-management/garbage-collector-roots).
Those2.34-series docs presently display2.34.9 and are supplementary to actual
pinned2.34.8 provisioning receipts; they do not establish that provisioning or
recovery has happened. Exact saved failures and proposed four-artifact/Task
syntax proof remain private for independent review; publish only sanitized
committed failure/recovery/provision/follow-up evidence after root acceptance.
