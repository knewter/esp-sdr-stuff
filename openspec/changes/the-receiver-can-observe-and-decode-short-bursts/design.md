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

### Recording correction after actual cost004 (UNVERIFIED)

The [actual read-only cost004 review](../../../docs/evidence/source004-actual-readonly-cost-004/README.md)
accepts current content and natural terminal evidence, but disproves complete
diagnostic conservation. Original phase export precedes two receipt reads and
the completed snapshot wrapper, losing two hash, two receipt and one snapshot
events. Historical fixture passes remain retained; tasks 5.2/5.3 reopen and
5.4/5.5 remain unchecked. Task 5.6 closes only its separately reviewed recovery,
provider and current-readiness prerequisites. No timing optimization is selected.

Implement a distinct mandatory final cumulative original-owner record after the
snapshot decorator returns, before snapshot returns to its caller. Keep the
original manager-close prefix, every content/ownership/closure predicate and
its order. Direct/query phases record their two receipt/hash pairs in the
original phase and finalize after those reads. A bounded outstanding-operation
witness requires zero unfinished measured operations; seal the recorder before
final persistence. Later attempts to record on it permanently refuse qualification.
Retrospective checks compare its sealed witness without reopening an expired
phase. Missing finalization never falls back to a valid prefix or terminal recorder.

Bind the typed final slot to the original phase index/deadline, prefix, ledger,
source, worker/request/result set and complete ordered event extension. Keep
the existing phase-plus-terminal-round history separate. Both Context and outer
consumers require complete raw-file inventories and exact final/prefix/witness
joins; omitted, extra, duplicate, late, changed or wrong-kind records refuse.
Retain all original event IDs, count cumulative IDs once, and count distinct
publication brackets separately. Final publication has its own returned
durability witness, charged to the original clock and persisted by the parent
and external terminal join. A payload does not measure its own later persistence.

The initial private changes are limited to costs, snapshot and their protocol
and Task recipe; retain the other 60 operational files and all existing test
bytes. Preserve all 231 named current source groups with zero skips and add
actual harmless normal/failure controls for complete finalization, missing and
mutated tails, sealed-recorder misuse, persistence, cancellation, keeper/FD/pending,
terminal rounds, deterministic content equality and external CLI joins. Whole
independent source/import/tool/archive review precedes root transfer and a
separately declared measurement. Original 13/45/30/32/165/300 clocks, cleanup,
producer and every physical gate remain unchanged. The private prospective
plan is pinned by SHA256
`9b8c3d0746999420f0e7ec72671c3ae0872e02984734dfeb4928f05c1fb7b9f4`.

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


## Whole-chain authority architecture004 (UNVERIFIED; proposed only)

This is a proposed refinement of the preceding ownership prerequisite, not
implementation or demonstrated host compatibility. Architecture002 failed whole
independent review, and003 required peer034 native-operation clarification;
preserve its119-file author bundle,133-file peer failure,003166 and034183 files,
literal five-case probe,161 passing historical assertions and every old snapshot.
The only owner is the existing holder. The launch/bootstrap/filter/resource
architecture expands tasks6.1/6.2 and requires independent prospective review
before code. Required behavior stays functional: declared normal source,
monitor, UART, controller-query, restore and release paths must be demonstrable;
a permanently refusing implementation cannot satisfy this plan.

### Trusted boundary and original clocks

The holder's exact pinned interpreter/import graph is a trusted single-thread,
no-internal-user-worker coordinator. It cannot trace itself. The existing external
Task/CLI observer binds its original process identity and actual terminal result;
the holder's own terminal is not proven by its saved marker. No second tracer or
guardian is introduced. Other admitted host tasks are traced before work; the
Docker daemon and native container process retain their separate original trusted
daemon/container proof, rather than being misrepresented as Docker-CLI descendants.
Host kernel, filesystem responsiveness, the private file namespace and absence
of arbitrary external same-uid memory modification remain trusted boundaries.
This is complete authority over the declared admitted workload, not a security
claim about arbitrary hostile host actors or a general sandbox.

Root-provided read-only metadata reports unprivileged uid1000, no effective
capabilities, Yama1, initially no seccomp filter, and kernel7.1.9-1-MANJARO. It
demonstrates neither SEIZE/filter installation/PIDFD_THREAD functionality nor
the complete kernel task-creation boundary. Supplementary tagged Linux6.12
source explains known holes but cannot qualify this host's kernel. All required
primitive semantics and workload compatibility need NEW harmless own-session
fixtures after plan review, with no global security change or privilege grant.

All added bootstrap, trace stops, resource/role admission, pumping, persistence,
real-parent waits and terminal effects are charged before and after to the
original applicable absolute role deadline. None creates a renewed allowance.
At the first failed-child cleanup or aggregate worker teardown, set once and
pass unchanged to all source/monitor/UART workers and their members:
min(original caller deadline, that first entry+30 seconds, holder first
cancellation+1800 seconds when present). Normal sequential source completion
does not start this clock. Original source45/native32 reserve, receiver
readiness30/acquisition180, monitor readiness15/capture240/whole260,
acquisition420, caller/holder5400 and holder first-cancel1800 remain. Prior
source qualification300 and producer165 are distinct. Caller, holder, keeper,
restoration and their terminal effects remain under original5400/1800 ceilings;
no short worker clock forces coordinator death during unresolved UART restoration.

### F1: Two barriers and exact unprivileged filter installation

Each root first execs a frozen, audited, single-thread bootstrap with a fresh VM,
an explicit safe inherited-FD list and no workload, child or kernel-user-worker
creation before INSTALL_WAIT. The holder directly retains the returned original
PID before any fallible metadata/log/identity effect, obtains its original
process pidfd under deferred cancellation, and SEIZEs with birth/exec/exit and
seccomp options before allowing filter installation. INTERRUPT and an actual
matching kernel stop establish bootstrap ownership. The bootstrap's blocking
INSTALL_WAIT is bounded by the root's original deadline; a failed constructor,
pidfd/identity write or cancellation retains partial-spawn authority and unknown
closure, rather than losing the child. There is no preexec_fn stop hidden inside
a Popen constructor's blocking exec-error pipe.

From that stop, the sole holder temporarily uses syscall entry/exit tracing for
the declared install prefix. It corroborates the native ABI and sole thread/
private unshared MM, verifies the exact no_new_privs request and actual0 return,
then captures the bounded sock_fprog length and every BPF instruction from the
actual seccomp(SECCOMP_SET_MODE_FILTER, flags=0, pointer) entry. The frozen
bootstrap has no writable/shared external mapping or concurrent writer to those
argument bytes between capture and kernel copy. Validate immutable argument
identity, ABI and exact expected BPF digest, then join the matching native syscall
success0 return. A sole thread and no preexisting undeclared filter stack are
required; NO_NEW_PRIVS, mode and filter-count observations are corroboration,
not substitutes for the entry/return/immutable-byte join. No privileged
PTRACE_SECCOMP_GET_FILTER or CAP_SYS_ADMIN operation is required or claimed.

Only afterward can READY be accepted. Workload GO is a second barrier after
exact role/command/FD/original-deadline admission. Filter stacking, removal,
undeclared exec ABI, ptrace by a tracee or an install mismatch faults the lineage
before unsafe execution; no JSON-only hash or higher-precedence hidden filter
can qualify. Inherited architecture-checked rules prevent CLONE_UNTRACED and
uncovered birth forms. clone3 ENOSYS fallback is an explicit compatibility
candidate requiring pinned-runtime positive proof. A forbidden operation uses
a selective trace/error/skip contract recording permanent failure while allowing
the admitted coordinator's existing finally/refusal path; no forced SIGSYS or
EXITKILL is substituted for unresolved physical restoration. Exact rule bytes,
ABI numbers, action precedence and fallback behavior remain to be implemented
and verified in the NEW private bundle.

### F2/F4: Every root and one wait owner

Direct holder roots include initial/repeated Git HEAD/status admission helpers
(original15-second helper bound), all Docker endpoint/image/ID/name/postflight
helpers (original10), controller preflight helper (original30, including its
existing8-second DBus query), initial keeper (existing5-second readiness),
replacement keeper, caller, cancellation/error cleanup helpers and final
endpoint/admission helpers. Enumerate every actual spawn branch, including
partial/error branches; no helper may work before original pidfd/role/deadline
capture and the two barriers. Before the first such admission helper, load the
saved actual-source4.3 qualification gate locally, verify the reviewed bootstrap/
tool launch binding, retain the existing original lock FD, and establish the
same-policy keeper. Moving keeper coverage earlier changes ordering, not its
EOF/RELEASE policy or original whole clock. Missing qualification performs no
runtime/archive query or device action. Unknown early-helper closure cannot use
the old no-caller shortcut to release. If initial keeper bootstrap itself fails,
the live holder retains its original FD and existing quarantine; no endpoint or
workload follows. A replacement uses only still-retained original FD authority.

All holder-spawned roots use a NEW private managed direct fork/exec handle, never
an ordinary Popen object or check_output/run/context/communicate convenience.
The immediate returned PID is retained in a cancellation-deferred ownership
record; fork failure has no child, while every later failure retains a child
record. The holder's same single thread pumps __WALL wait events, including
non-SIGCHLD births, while servicing bounded nonblocking pipe I/O, cancellation,
role IPC and deadlines. The handle reads only a cached actual terminal state;
its destructor does not wait/poll or enter subprocess._active. No second thread,
Popen.poll/wait, context exit, _active cleanup or unrelated waitpid consumes
holder-owned stops. SIGCHLD disposition and all actual wait consumers are bound
in the source/runtime map. Stops and PTRACE_EVENT_EXIT are not exit codes;
ECHILD and WNOHANG0 never establish successful closure.

Inside traced caller/helpers, unchanged historical Popen helpers may retain
their real-parent terminal waits only through reviewed adapters: the holder
owns tracer notifications, then the real parent receives and joins the actual
terminal notification. This distinction covers every inherited helper, source,
monitor, acquisition, restore/boot, dispatch and native wrapper path. No saved
returncode manufactured from a tracing stop qualifies. Application cleanup
and external forwarding require fresh original individual pidfd authority;
missing or ambiguous authority refuses unsafe signaling and retains quarantine.
Immutable native internal member/self-signal operations instead use the explicit
kernel-mediated contract below, preserving the original no unsafe numeric signal
wording. No application IPC is fabricated for a native binary and no numeric
group cleanup exception is introduced. Positive and negative paths need proof.

Keeper is a separately admitted no-fork root under the same tracing owner, with
EXITKILL absent and its exact existing lock/control FD and EOF/RELEASE semantics.
It is not a worker30 target. Normal release needs its actual0 terminal, original
FD acknowledgment and the original holder marker/terminal chain within5400/1800.
Caller is likewise a coordinator, not a worker. Native/container processes are
not silently pulled into host ancestry: exact CID/name/image, both ID/name
absence, disable/remove ACK0 and socket OFF remain separately required, and
forced container cleanup cannot count as natural timed qualification.



### Native internal members and signals: kernel-mediated transactions

This clarifies peer034's material NATIVE_MEMBER_SIGNAL_TRANSACTION_PROTOCOL gap.
Immutable Git/Docker/Go/CGO/native binaries cannot emit new application messages.
They stay unchanged. No unsafe numeric signal remains the original requirement;
it is not replaced with the stronger, incompatible rule that every native
self-signal must use a new application IPC or a pidfd syscall in the binary.
The sole holder distinguishes four explicit transaction classes: direct managed
holder roots, application logical-role spawns/transitions, native internal threads,
and finitely predeclared native internal helper processes. All share the complete
original birth/resource/exec/terminal ledger and original clock accounting.

Before root GO, freeze a native operation profile for each exact admitted root:
original process/TGID/task lineage and pidfds, ELF wrapper and executable hashes,
all loaded source/library/patch/build/ABI provenance, root argv/environment and
relevant Git/helper/plugin configuration, finite permitted creation flags,
signal/exec/resource semantics and original role/deadline. The selected Docker
ELF wrapper and native executable were only read as static bytes: native SHA256
`d0f9bb5d7eb5ac3c10b358b75bd194a1135f4add37689dcf85d93801c2fe052b`
contains Go1.26.7, CGO_ENABLED=1, linux/amd64/v1 build info. Locked nixpkgs source
selects Docker29.8, Go1.26.7 and Git2.55. Tagged matching primary code and pinned
package/patch files identify operation classes; they do not establish exact
patched runtime profile completeness or current-host compatibility. Include Go
raw clone and CGO/glibc pthread paths; proving only one of them is incomplete.

The inherited exact filter routes every covered ordinary birth, native signal,
exec and resource-changing syscall to a canonical holder kernel-entry transaction
before effect. The canonical entry joins actual kernel-reported calling TID,
retained original task pidfd/lineage and current TGID, exact syscall ABI/number,
register arguments, frozen native code/profile mapping and admission epoch.
Seccomp and syscall-entry notifications for the same call join one sequence;
they cannot create duplicate admission. Mutable userspace declarations, PPID or
PGID membership scans are not the source of authority. The supported kernel's
event order, flags, namespace mapping and syscall-entry/return mechanics must be
proved later; this proposal asserts no actual primitive result.

For an internal thread, the holder matches one finite profile row, including
CLONE_THREAD/shared-MM/files/sighand/exit-signal/TLS/tid flags and bounded pointer
arguments, while excluding UNTRACED/namespace/uncovered ABI forms. It creates a
pending native-birth record from that actual original creator before permitting
the syscall. Actual parent birth event/GETEVENTMSG, returned child TID and the
newborn's actual stopped event must all reconcile, in either parent-first or
child-first order, to the original root and calling TID/TGID. Acquire original
thread pidfd authority before resume and retain every child record even if
metadata/cancellation/partial spawn fails. The thread inherits exactly its
existing root role, resources, GO epoch and absolute deadline; it does not start
a source episode or receive another per-thread time budget. Kernel birth history,
not a thread's lack of application IPC, permits this internal member. A missing,
duplicate, incompatible, late or ambiguous kernel transaction keeps the child
stopped/failed and preserves refusal. No blanket native-descendant permission.

Native internal process helpers require a separate finite predeclared row bound
to the original root invocation and source/config branch. Their actual creation
entry and stopped child are owned before any body; a source-audited bounded
pre-exec prefix may perform only its declared setup operations under the inherited
filter. Before the helper image can run, join actual exec-entry argv/environment/
FD resources and exec event/stopped image to the exact declared command/code
hashes. Wrapper-to-real-program exec is likewise explicitly bound. A new image,
hook, plugin, daemonized member or namespace/resource path is not inferred from
native ancestry: it must match that row or fail before unsafe work. An internal
helper retains the same logical role and original absolute bounds; creating a
new source/monitor/UART role, endpoint or restoration transition still requires
the mandatory authenticated application transaction. Neither internal thread nor
process admission can reopen a sealed worker GO epoch. The existing kernel-user-
worker/io_uring/vhost boundary remains fully required.

Native self-signal requests are captured at actual kernel entry, not invented
application messages. A finite profile matches signal number, target form,
native semantics, original issuing task/root and exact retained target process/
thread pidfd. Unknown, stale or contradictory numeric identity is not signaled.
For the narrowly allowed self-group contract, actual tgid must equal the issuing
task's retained currently live original logical thread group in the unchanged
PID namespace. The target must be its original live registered member, with
fresh stopped identity/pidfd reconciliation. Stop other same-group birth/exec/
exit-capable actors and drain outstanding events before permitting the effect;
hold that sealed target/group frontier through the actual syscall return. The
issuing original task stays live in the syscall, so its own TGID cannot be reused
by another process during the effect. No new same-group task can replace a target
TID while this frontier is held. An exec transfer first retires old bindings and
requires fresh current-group reconciliation; cached pre-exec TIDs do not qualify.

Only these numeric forms may be considered safe after that complete join:
tgkill with positive TGID equal to the issuing live original group and target
equal to a retained original member; positive kill of that same original TGID
with the original process pidfd and conserved member frontier; or tkill only
the exact currently issuing original TID. tgkill's kernel TGID check also rejects
a target TID recycled into another group; it is not permission to skip original
target authority or same-group birth sealing. Plain tkill of a peer TID, negative/
zero group kill, foreign TGID, unknown/reused numeric target or unbound signal
semantics never receives this exception. A known completed target is not a live
target: the holder suppresses the effect and returns the separately audited
no-target error only where the exact source profile permits that natural race;
unknown/mutated identity remains failed, without a numeric signal. Mark a
skipped/holder-denied syscall and its emulated error as such, distinct from an
actual kernel syscall-return event; never fabricate an actual kernel success.
Preserve native success/error, original signal-delivery stop/siginfo/reinjection
through exact retained tracee authority, and actual terminal distinctions.

This narrow kernel-native self-operation contract does not broaden external
cleanup. Caller/holder forwarding, other-role termination and native requests
to another process still require the original individual target pidfd and
original ownership/deadline/cleanup policy. Native external numeric calls are
stopped before effect and either handled by an independently reviewed exact
pidfd-based adapter with matched native permission/payload/siginfo semantics, or refused without unsafe
action; absence of application IPC cannot silently authorize them. No numeric
PGID stop or leader-only cleanup is introduced. Natural positive paths must work;
ambiguous forced cleanup stays failed with the existing keeper/pending policy.

The sole pump conserves native entry/birth/child-stop/profile/exec/signal/return/
delivery/terminal events in the same worker and later helper frontiers. Native
transactions consume original role/worker/coordinator budgets before and after;
no new clock or renewed cleanup allowance. Later6.2 proof must genuinely run the
exact unchanged selected native tools in harmless no-endpoint positive fixtures,
record the native classes they actually exercise, and separately cover forbidden
flags, native child-before-parent order, missing/duplicate entry, unknown helper,
same/foreign-group numeric reuse models, dying target, exec transfer, native
self-signal/no-target semantics and original external cleanup refusal. Merely
executing --version without exercising a required class is not that class's
proof. Preserve all161 historical assertions, literal failing probe, full sources/
imports/profiles/maps/archives and actual external CLI0/failure. No native binary,
kernel primitive, endpoint, daemon, producer or device was executed by this
planning author; compatibility, complete kernel profile and timing remain
UNVERIFIED. A permanently refusing implementation is not readiness.

### F3: Supported kernel/ABI/FD-resource contract

Tracing fork/clone alone is incomplete: kernel6.12 io-wq and vhost source show
user workers created through kernel paths without ordinary ptrace birth events.
Qualification must bind the actual supported kernel release/build/config and
corresponding source, enumerating every reachable copy_process/kernel_clone/
create_io_thread/vhost_task/user_worker call site and its ABI, syscall, device,
ioctl and inherited-resource trigger. This finite coverage map is a mandatory
before-GO input, not a vague assumption that a birth filter is a sandbox. Unknown
kernel variants or uncovered reachable paths fail qualification; the declared
normal workload must still have demonstrated positive compatibility.

The declared resource profile excludes all io_uring_setup/enter/register calls,
ring file descriptors, ring mappings, inherited/transferred rings and SQPOLL
resources; setup denial alone does not close inherited/SQPOLL worker creation.
Fresh bootstrap exec removes inherited VM mappings. Its exact inherited FDs are
only typed original lock/control/role/log pipes and admitted stdio; no ring,
vhost, arbitrary driver, namespace or delegated task-launch resource is allowed.
The trusted holder creates no such resource and imports no implicit worker pool.
Tracee FD creation, open/dup/transfer and receiving paths are included in the
finite ABI admission map. No SCM_RIGHTS, pidfd_getfd, inherited external socket
or equivalent unreviewed resource injection is admitted. Existing dbus-next
explicitly keeps negotiate_unix_fd=False; pinned reader code then uses stream
read rather than ancillary recvmsg. Changing this option would need a new plan.

vhost reachability is excluded through the resource provenance and typed
open/ioctl policy, not merely CLONE_UNTRACED. Before resource-changing calls,
the holder joins their actual calling task, FD provenance, immutable decoded
arguments and finite allowed operation. Pointer-bearing arguments require an
actual stopped barrier for every sharing-MM/FD-table writer through syscall
completion; a racy pathname/JSON snapshot cannot qualify. Fresh FD results are
joined at actual return and may not be used before registration. Deny unknown
FD classes and vhost worker-triggering request paths before effect. UART/stdio
retain the exact required pinned pyserial/termios ioctl paths, bound to the
identity-selected UART/stdio FD class; numeric request collisions on other
devices cannot inherit that permission. Required ordinary socket, regular-file,
pipe, thread and runtime operations are admitted by an explicit finite profile
and later real positive fixtures, not by a blanket ioctl or device whitelist.

Architecture checks cover supported syscall ABIs and multiplexed operations;
uncovered compat/x32 or worker-producing resource APIs cannot bypass the gate.
The supported-kernel callsite/resource audit must account for all remaining
trace=0/user_worker cases, and either show them unreachable under the pinned
profile or give original authority before they can run. No privileged kernel
hook, cgroup mutation, global seccomp policy or actual daemon/device probe is
authorized here. Tag6.12/master evidence identifies holes only; compatibility
and complete coverage on kernel7.1.9 remain UNVERIFIED.

### F5: Exec lineage without fictitious old-thread death

The ledger separates append-only task-birth records from logical process
lineages. Process pidfds refer to kernel PID/process identity; they are not
immutable physical-task handles across nonleader exec de_thread. A traced
nonleader exec may lose its former TID and retire other thread identities
without an ordinary wait terminal for that former TID. PTRACE_EVENT_EXEC's
former TID, stopped survivor, pre-exec task/TGID records and retained original
role/deadline establish a typed EXEC_TRANSFER_RETIRED transition. Preserve old
records and retired signal bindings; do not rewrite them or require an
impossible old-TID death. Acquire/reconcile the survivor's current process and,
where supported, PIDFD_THREAD authority while it remains stopped, before
resuming or signaling. Ordinary leader exec, rapid thread-group exits and
nonleader exec races receive distinct controls. Any ambiguous transfer fails
the lineage and keeps refusal; no numeric PID reconstruction is allowed.

Each task birth must reconcile to actual observed terminal or a proved typed
exec-retirement/transfer. The surviving logical process still requires actual
terminal and complete thread-history conservation. PIDFD_THREAD readiness and
pidfd/wait semantics on this host are not asserted by documentation or modeled
records; actual own-session controls must establish them before readiness.

### F6: Real tracer loss and surviving actors

Without EXITKILL, real holder/tracer death normally detaches and may resume
existing tracees. Architecture004 routes covered native calls through RET_TRACE;
where the exact filter is already installed, the kernel's documented no-tracer
error prevents those covered calls from taking their ordinary effect. This is
conditional on the installed filter and supported kernel, not an actual host
result. Already-born tasks, in-flight operations and unqualified coverage remain
conservatively unknown; no dead tracer can join their history or closure. The
design makes no dead-tracer membership or frozen-tree claim. Later proof must
separately exercise actual detach/continued execution, already-in-flight births,
and the exact no-tracer return of every covered birth/signal class. The admitted caller retains a
dedicated holder-liveness channel/original holder identity, whose writer is
not inherited by helpers, and checks it before and after every role transaction,
new endpoint/device action, restoration decision and release request. Channel
EOF, lost holder authority, malformed role reply or storage fault invalidates
completion, stops new actions and preserves the existing private/shared pending
and quarantine state; no fresh scan or replayed receipt reconstructs a ledger.
Already in-flight restoration may finish its existing OS helper; forced
coordinator kill is prohibited and no completed/qualified release follows
without original known closure. This is not a promise to undo an external
operation that had already begun before unexpected holder death.

The existing keeper remains the surviving lock actor: loss/malformed control
uses the unchanged indefinite-hold behavior, ignoring its existing SIGINT/TERM
signals. Holder-only death closes its sole control writer and invokes that
policy. Keeper-only death with a living holder faults completion; the existing
replacement path may retain the lease only from still-held original FD
authority, never by reacquiring a consumed number or changing release policy.
Caller-only death is a failed lineage handled by live holder with original
authority; all restoration/endpoint decisions still require complete known
source/monitor/UART/container closure. Combined channel/storage/caller/keeper
faults never authorize release or claim complete process absence. If all trusted
lease-holding actors/FDs are destroyed by host failure, the design cannot retain
a nonexistent lock or recreate exact authority; the external actual CLI and
required complete proof still refuse qualification. State that trusted-host
destruction limit explicitly, without inventing a guardian or new keeper policy.
Holder death after an otherwise proven release likewise cannot fabricate an
actual terminal0; saved completed-looking bytes alone remain unqualified.

### F7: Authoritative birth, role and terminal barrier

Root states are PREPARED, FORK_CAPTURED, BOOTSTRAP_STOPPED, INSTALL_PROVED, READY,
GO, ACTIVE and typed terminal/failure. Any post-fork exception retains ownership.
Newborn kernel stop and parent birth event may arrive in either order. Keep
unclassified stopped tasks and incomplete parent/child events in a pending
registry, never resume/drop them, and join GETEVENTMSG, original birth identity,
pidfd, actual spawning TID/TGID, admitted parent lineage and role before GO.
CLONE_PARENT, reparenting, setsid, non-SIGCHLD clone and vfork do not obtain role
authority from mutable PPID or process-group scans. Exact event history supplies
lineage; /proc is corroboration rather than a census proof.

Caller/helper application-role IPC uses an authenticated private channel and one outstanding
transaction per actual spawning task, naming immutable command hash, role,
child budget, nonce and original absolute deadline. Only the declared actor
holds that writer; it is not passed to unrelated children. Kernel syscall/birth
event and stopped newborn must join that actual TID/TGID and pending request,
not a nonce alone. This IPC rule applies to application logical-role transitions;
native internal births/signals use their exact kernel/profile transactions above,
not an impossible message from immutable binaries. Missing application-role IPC
or missing native kernel/profile transactions both fail their respective class.
Duplicate/spoofed/delayed transactions, cross-thread requests and undeclared
births permanently fail the lineage while preserving
stopped authority and existing refusal. No late register/resume may repair a
formerly unowned workload interval. Existing nested helpers get explicit
adapter transactions without modifying historical source bytes.

Closure is a sealed conservation frontier. Before evaluating worker closure,
the holder obtains actual stops for every live coordinator/root capable of
requesting or creating another worker and drains the kernel events generated
before those stops. At that barrier it seals the source/monitor/UART GO epoch,
joins every outstanding request/birth/child-stop transaction and forbids future
worker GO. Coordinators may then resume only in the explicit finalization epoch,
whose permitted restore/postflight helper births still stop and register before
workload and are conserved in a separate helper frontier. An ordinary late fork
cannot run an undeclared worker: it remains stopped and permanently fails the
handoff. Repeat actual coordinator stops and event/request joins for the final
helper frontier before release. Stops are not terminal; live coordinators and
keeper keep their original bounds and authority until their own later joins.
Every originally registered worker birth and transferred exec lineage must have
an actual terminal or justified typed retirement; there can be no live worker-capable birth source, unclassified
stopped child, outstanding parent/child event, role/bootstrap/GO transaction,
unjoined real-parent wait, pending resource transition or unfinished charged
log/fsync/receipt/FD effect. The live coordinators and keeper are explicit
exclusions with separately sealed spawning frontiers and their own later
terminal joins; they are not absent workers. The single pump correlates all
original histories and actual terminal observations. WNOHANG0, ECHILD, leader
reap, empty mutable tables, body markers and PTRACE_EVENT_EXIT cannot establish
this barrier. Late birth/exec/role events or lost history keep the frontier
failed and prevent endpoint/restoration/release.

After proven worker and exact container closure, original restoration may run
through admitted, traced helper roots under original coordinator bounds. Seal
all helper frontiers and actual terminals before keeper RELEASE; then join
keeper actual0, original parent-FD acknowledgment, root-FD effects, private and
shared markers, actual holder terminal and external CLI status. Restore/boot
helpers and final admission/endpoint helpers are accounted for too. Actual
natural exit0 with complete history differs from forced cleanup. No new30-second
clock starts after restore. Cancellation/late/storage/FD faults are permanent
qualification failures even if a later body emits successful-looking bytes.

### Evidence and planning/implementation boundary

Use the NEW bundle's pinned declared Python/Task/OpenSpec tools only. First prove
bootstrap/filter exact-byte entry/return, every direct root and partial spawn,
all wait consumers, resource-injection/io_uring/vhost refusal with required
positive runtime/UART-modeled/controller-fixture paths, child-first/parent-first
events, role spoof/duplicates, CLONE_PARENT/non-SIGCHLD/vfork, nonleader exec,
late descendants, original pidfd reuse controls, live and dead tracer failures,
keeper/channel/storage/cancellation faults, durable FD/log effects and actual
external CLI0/failure. Genuine OS tests are harmless own-session fixtures after
review; modeled cases are labeled. No actual source/controller/daemon/store/
compiler/device operation belongs to these author tests. All161 unchanged
historical assertions and literal five-case failing probe stay byte-exact.

Freeze complete NEW sources, transitive imports, supported-kernel/ABI/resource
profile, exact filters, old/new maps, pinned commands, actual Task terminal logs,
raw failures and full archives. Independent whole review precedes root6.3
byte-only transfer. Missing actualsource4.3 still blocks operational freeze;
no dummy qualification, prior FPGA result or historical helper baseline supplies
it. Only a later sole-root fresh complete runtime/admission proof permits one
separately frozen physical condition; no RF requirement, checkbox or registry
is promoted by this proposal.

Primary references: [ptrace](https://man7.org/linux/man-pages/man2/ptrace.2.html),
[seccomp](https://man7.org/linux/man-pages/man2/seccomp.2.html),
[filter ABI/precedence](https://docs.kernel.org/userspace-api/seccomp_filter.html),
[pidfd](https://man7.org/linux/man-pages/man2/pidfd_open.2.html),
[clone](https://man7.org/linux/man-pages/man2/clone.2.html),
[io-wq](https://github.com/torvalds/linux/blob/v6.12/io_uring/io-wq.c),
[vhost](https://github.com/torvalds/linux/blob/v6.12/kernel/vhost_task.c),
[de_thread](https://github.com/torvalds/linux/blob/v6.12/fs/exec.c), and
[ptrace teardown](https://github.com/torvalds/linux/blob/v6.12/kernel/ptrace.c).
These support hazards and proposed constraints, not actual host qualification.
Pinned CPython/dbus-next/pyserial source observations, prior full failures and
exact downloaded reference bytes remain in the private prospective003 handoff.

Native clarification primary sources: [tgkill/kernel target matching](https://github.com/torvalds/linux/blob/v6.12/kernel/signal.c),
[Go1.26.7 Linux runtime](https://github.com/golang/go/blob/go1.26.7/src/runtime/os_linux.go),
[Go CGO pthread startup](https://github.com/golang/go/blob/go1.26.7/src/runtime/cgo/gcc_linux_amd64.c),
[selected Docker29.8 main](https://github.com/docker/cli/blob/v29.8.0/cmd/docker/docker.go),
[Git2.55 preload threads](https://github.com/git/git/blob/v2.55.0/preload-index.c), and
[glibc2.42 pthread target precautions](https://github.com/bminor/glibc/blob/glibc-2.42/nptl/pthread_kill.c).
These tagged sources and static selected-tool metadata support operation classes
and the proposed boundary; they do not prove actual complete patched profile,
current-host syscall semantics, functionality or timing.
