## 1. Measure event observation

- [ ] 1.1 Define a repeatable owned source with at least 100 counted emissions and documented duration/bandwidth; check the selected capture window can fit it.
- [ ] 1.2 Record captures and compute hits, complete bursts, misses and uncertainty relative to source ground truth.

## 2. Evaluate a bounded decoder

- [x] 2.1 Choose a decoder for an actually captured, complete waveform and document its input format; verify a known payload rather than visual resemblance. Proof: [four independently replayed packets](docs/evidence/ble-owned-decoding/README.md) and [10-bit example](docs/evidence/ble-controls-decoding/README.md).
- [x] 2.2 Publish the capture/decoder manifest, summary plots and application matrix with useful/limited/not-demonstrated outcomes. Proof: [manifests, amplitude plots and application matrix](docs/evidence/ble-owned-decoding/README.md), [control-sweep manifest](docs/evidence/ble-controls-decoding/README.md).

The five packets verify their protected PDUs and exact owned AD, with complete
packet windows inside the captures. They do not establish 100 emitted events,
missed-event rates or reliable detection in three repetitions. The first two
tasks remain open; registration counts and snapshot counts are not emissions.

[The predeclared accounting tool](docs/research/ble-counted-trials.md) is ready,
but [three finite source-only diagnostics](docs/evidence/ble-counted-source-smoke/README.md)
produced no actual termination counter. Their accepted requested limits do not
close task 1.1 or supply input to task 1.2. Keep the three receiver trials pending
until the independent source-count gate passes.

## Proof procedure

Physical proof: 100 counted emissions plus capture timestamps and a saved waveform; offline proof: run the selected decoder on the pinned capture and compare output to the known payload. No decoder or protocol support is assumed in advance.

Required outcome: At least 100 deliberately emitted repeat events with ground-truth counts and capture hit rate; a decoding claim includes a complete waveform and verified payload.

## Subsequent diagnostic checkpoint

The [single reachable legacy100 count diagnostic](docs/evidence/ble-count-limit-100-001/README.md)
also retains actual `0x3c/count0`, with [independently verified cleanup](docs/evidence/ble-count-limit-100-independent-review/README.md).
It supplies no usable emitted denominator. A separately prospective
[extended100 source-only condition](docs/research/ble-extended-count-limit-100-protocol.md)
cannot qualify the original legacy255 reports or close either event-observation task.

The [actual extended100 report](docs/evidence/ble-extended-count-limit-100-001/README.md)
does observe controller count100, but the full monitoring lifecycle fails.
Neither its auxiliary-channel payload nor that failed episode supplies the
original legacy marker denominator. Original event-observation tasks stay open.

[Timer source diagnostics](docs/evidence/ble-duration-source-diagnostics/README.md)
observe termination events with actual count zero. The [ten-episode RF
discriminator](docs/evidence/ble-zero-counter-rf/README.md) preserves 262
snapshots but yields no CRC-valid owned packet. Its null result is inconclusive,
and its scheduling deviation remains recorded. These diagnostics establish no
≥100-event denominator, hit rate or task 1.1/1.2 acceptance.

The [independently replayed advertising-mode pair](docs/evidence/ble-mode-counter-independent-review/README.md)
accepts ten source commands and verifies both original source/monitor
terminations. Legacy and extended modes both retain `0x3c/count0` with
complete cleanup. Their count gates remain failed; this supplies no emitted
denominator, fresh hidden-SDR packet or closure of task 1.1/1.2.

The [independently reviewed matched gain controls](docs/evidence/ble-matched-gain-independent-review/README.md)
reproduce one fresh complete owned packet in manual ten-bit capture 48 and
retain zero owned packets in the hardware-gain condition. All 1,994 transport
records, source cleanup and full restorations pass. No emitted denominator or
three-response result follows, and tasks 1.1/1.2 stay unchecked.

The [October 3 readiness condition](docs/evidence/ble-extended-count-limit-100-readiness-review/README.md) passes typed controller count100 in both readers, normal monitor completion and cleanup. Extended auxiliary-channel AD supplies no original legacy-channel air denominator or reception hit rate. Tasks 1.1/1.2 and original Trial B gates stay open; earlier failed diagnostics remain retained.

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

## Fresh original eight-bit control

The [October 4 control](docs/evidence/ble-bluez-control-003/README.md) completes
three source ON/OFF pairs,1,260 independently verified snapshots, normal monitor
cleanup and full original 4 MiBrestoration. Entire decoder replay retains zero
CRC-valid packets; fixed prospective-band scalar replay supplies no reciprocal
source attribution. Sparse windows and unknown air emissions make this a null
control, not a detection-failure or missed-event rate. Original Trial B remains
gated. The next separate bridge-profile ladder starts ten-bit/BW20/manual48
and isolates precision, gain and bandwidth; earlier results remain unchanged.
No original task checkbox or accepted requirement changes.


## Ten-bit ladder control and fuller metadata

The [independently reviewed ten-bit/BW20/manual48 control](docs/evidence/ble-bluez-control-004/README.md)
verifies all 1,010 snapshots and full original restoration. Whole decoder replay
finds zero owned packets and three redacted CRC-valid packets from other sources;
these do not establish owned-source reception. Fixed-band scalar controls show
no repeated source-attributed rise. The next ladder condition is
8-bit/BW20/manual48, followed by 8-bit/BW20/hardware. Source ground truth and
original Trial B gates remain unmet; no physical checkbox changes.

The [fuller HCI parser](docs/evidence/ble-hci-metadata-preparation/README.md)
passes 134 focused checks and 23 independent probe groups. It retains additional
redacted requested fields for future profile validation. Earlier trial records
remain bound to their older helper; no omitted field, emitted PHY/power, air
count or reception is inferred from this software preparation.


The [next eight-bit/manual control](docs/evidence/ble-bluez-control-005-failed/README.md)
failed a short UART payload during its third source phase. All 1,047 saved
complete payloads and original restoration pass independent audit; the failed
fragment was not saved. Interrupted monitoring and a truncated source phase
prevent complete schedule/scalar qualification. Preserve this failed condition;
zero saved-row integrity failures does not describe the failed read. No task
or accepted requirement changes.


The [BW20/hardware condition](docs/evidence/ble-bluez-control-006/README.md)
completes all source pairs, 1,257 intact snapshots and original restoration.
Independent full decoder/scalar replay retains zero CRC-valid packets and no
repeated source-attributed nominal-band rise. HCI completions lie within the
predeclared guards; DBus acknowledgements alone are not synchronous completion.
The original BW12 condition is next after reviewed prefix retention. Original
Trial B and count/detection gates remain open; no checkbox changes.

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

- [x] 3.1 Verify exhaustive signed upper-bit equivalence and independent packing; freeze every original/derived waveform and replay identical bounded decoder settings. Proof: locked offline tests, per-row lineage and paired outcomes.
- [x] 3.2 Independently verify changed owned outcomes and publish the bounded digital-precision result, retaining every row and all original radio gates. Proof: independent whole replay and protected packet/window checks.

Both offline diagnostic tasks are grounded in [the complete paired record and independent review](docs/evidence/ble-same-waveform-precision/README.md): all1,256 original/derived rows, two unchanged owned packet pairs, exhaustive conversion and nine corruption probes pass. These two supporting tasks do not close original physical tasks1.1/1.2 or alter TrialB.

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

## Fixed zero-data primary receiver outcome

The [independent whole receiver review](docs/evidence/ble-primary-zero-data-receiver-001-review/README.md) verifies all 365 ten-bit waveforms, three monitored count100 controller phases and full original 4 MiB restoration with reset boot. The unchanged primary decoder finds zero owned or foreign CRC-valid primary packets. Guarded ON captures are 3/4/4; 347 OFF and seven boundary captures remain accounted for. Low snapshot duty makes this null inconclusive. The 300 controller events are not independently counted primary emissions; source attribution, detection/miss rates, three reciprocal RF responses and original Trial B remain unproved. No physical acceptance task or accepted requirement changes.

## 4. Evaluate separately timed primary opportunity (UNVERIFIED)

The [prospective timed-v2 protocol](docs/research/ble-primary-timed-zero-data-v2-protocol.md)
adds a separate diagnostic after the completed fixed365null condition. It leaves
original tasks1.1/1.2, Trial B, accepted requirements and all old receipts unchanged.
Software tasks 4.1 and 4.2 are grounded in [independent source and root transfer proof](docs/evidence/ble-primary-timed-source-host-preparation/README.md). Caller admission and physical tasks remain unverified.

- [x] 4.1 Implement/test a separate fixed native timed-v2 source and container helper; preserve v1 source/guards/low-level/image behavior and exact2036 power/ACK parsing. Proof: locked Task exact-wire/timer/typed-count/cancellation/cleanup tests plus unchanged-v1 source and regression comparison, retained failed attempts.
- [x] 4.2 Add a separately tagged immutable Nix source-bearing v2 archive and explicit Task entrypoints. Proof: sole-root archived-source/runtime/entrypoint/config byte freeze and unchanged-v1 archive comparison; no mutable-tag fallback. Refresh affected production source tuples and any later strict register artifact after merge.
- [ ] 4.3 Implement/review separate source004 and NEW outer gate before freezing current v2 caller/runtime/controller/endpoint/image admission and operating one bounded qualification. Preparation proof: hermetic pre-monitor pinned selection under165/300; all fresh local verification inside45; complete bounded worker/keeper ledger, natural closure and truthful terminal fault tests; independent current-provider/full-proof/frontwork timing. Physical proof: matching full native/independent monitor profile, five ACK0 pairs, one actual timer0x3c, typed agreeing UINT8 count metadata,24-to-less-than30-second observed enable interval, natural owned closure and unchanged postflight. No air denominator or retry.
- [ ] 4.4 Adapt NEW private receiver support/dispatch/account/caller/holder and qualify the v2 receipt; leave old15 inputs/holder/receipts exact. Proof: locked Task slow preflight/freeze/fsync/spawn/closure/boundary/cancellation/quarantine tests, actual inherited harmless process/flock fixtures, whole transitive source/runtime/import/archive freeze and independent current root transfer review.
- [ ] 4.5 Operate one separately frozen180-second ten-bit/BW20/manual48 condition with unchanged placement/decoder and three25-second ON episodes. Physical proof: inclusive45-second episode clocks, actual initial/OFF/tail bounds, complete raw integrity and failed-prefix retention, source3 closure before ready+165,100 guarded ON brackets total and25 per repetition, full original4MiB restoration/reset boot. Sparse coverage remains failed opportunity without retry.
- [ ] 4.6 Independently replay every saved waveform and exact monitor/source/ownership/clock/restoration join, publishing sanitized counts and limitations. Proof: unchanged blind parser/decoder invocation over the complete capture manifest plus independent saved-only receipt; no rate/air-count/three-response/Trial-B claim without its original proof.

The [actual timed source001 failure and reviewed recovery](docs/evidence/ble-primary-timed-source-001-failed/README.md) stopped during monitor identity startup before any source command. Task4.3 remains open; recovered ownership is not timer qualification. Retain this attempt while correcting and independently reviewing new startup preparation.

[The later source003 cost refusal](docs/evidence/ble-primary-timed-startup-preparation-review/README.md)
admits no source/monitor attempt. The [source004 prerequisite](design.md#source004-bounded-verification-prerequisite)
preserves every old receipt and all original physical requirements. Its planning
review is not implementation, actual timing fit or source-only qualification.

## 5. Attribute source004 verification cost before optimization (UNVERIFIED)

This supporting software group is a prerequisite of4.3, not an additional
receiver condition. Its scope is [bounded instrumentation and conditional
alternatives](design.md#source004-cost-attribution-before-optimization-unverified).
Host tasks5.1–5.3 pass [whole independent preparation review](docs/evidence/ble-primary-timed-source004-readonly-review/README.md); actual measurement and attribution remain open. Implement only after this scoped plan is committed and
reviewed by root; batching, census reuse, archive-read changes and rescheduling
need a later attribution-based plan revision before implementation.

- [x] 5.1 Freeze a NEW instrumentation-only private bundle from the exact47-file corrected003 baseline and143 author/24 peer no-skip receipt, preserving every original predicate, clock, producer/worker ownership and cleanup boundary. Proof: complete source/byte-map comparison, retained old receipt SHA, explicit changed-file list and no actual Nix/store/daemon/controller/compiler/device operation.
- [x] 5.2 Add bounded private operation brackets/counts for worker CLI, parse/hash/tool checks, process census, each existing fsync, durable outputs/ledgers and seal/terminal validation; record individual worker body completion inside its payload separately from parent receipt/group absence/terminal observation. Bind dynamic diagnostics to a NEW per-phase ledger/sidecar rather than deterministic fresh-content tuple equality fields. Proof: fixture event/request/result conservation, differing-timing/equal-content comparison, overlap-aware aggregation, exact graph/shard/archive/tool identities, bounded private numeric/hash fields and charged original deadline checks; no change to admission behavior or extra per-event fsync.
- [x] 5.3 Verify logging overflow/missing/duplicate/partial/changed/late events, persistence faults and cancellation retain failures and original pending/keeper quarantine. Proof: replay all143 corrected003 author groups with zero skips and targeted inherited-flock/owned-descendant/injected-clock/descriptor-reuse tests; independently review the expanded immutable source map, event schema and complete saved results.
- [ ] 5.4 After independent host readiness, have the sole root operator freeze and execute one declared bounded read-only whole current-tuple measurement, capturing actual CLI terminal, full reference/NAR union, all imports/tools and both whole archives. Proof: retain complete305/1220/14 baseline or actual expanded closure with no dropped roots/inputs,47 baseline private files plus all additions/binding,22 project bytes and every actual import, whole ownership/FD/terminal ledgers, original13/45/30/32/165/300 clock scope and immutable event/raw-evidence hashes; independent saved whole review. No source or receiver action and no automatic retry.
- [ ] 5.5 Publish sanitized measured costs, attribution limits and a fit/refusal recommendation; select at most the smallest justified optimization for a separately reviewed plan revision. Proof: replay the complete captured event stream against raw ledger brackets/counts, separate measured wall/CPU/static counts/inference, and show all frontwork plus native32 fit within source45 with credible margin or explicitly retain failure; root current full proof remains distinct from physical source qualification.

Narrow proof experiment:5.1–5.3 use the NEW immutable bundle's explicit pinned
Task host-fixture recipe and independent saved replay, with named143 baseline
groups, all new groups, zero skips, exact source-map/command/result hashes and
retained failures.5.4 is a separately recorded sole-root read-only experiment;
5.5 is saved-only whole event/ledger analysis and independent review. No cheaper
fixture or older Forgix proof substitutes for5.4. Software completion cannot
check4.3's physical qualification,4.4–4.6 or1.1/1.2.

### Exact provider preparation before one NEW cost follow-up (task5.6) (UNVERIFIED)

Tasks5.1–5.5 retain their original intent and checkbox state. This software
dependency task addresses the retained root cost003 missing-selected-provider
failure; it is not a source optimization, measurement success or physical gate.
See [design](design.md#exact-provider-preparation-and-one-new-cost-follow-up-unverified).

- [ ] 5.6 Preserve all43 failed cost003 outputs/start/terminal/transfer receipts and independently qualified keeper/quarantine recovery; implement/review a small locked-flake Task to realize and persistently GC-root only the exact selected Nix provider outside measurement. Proof: complete retained failure and recovery join, exact immutable Git/lock/provider/derivation/root/closure/executable/config/actual Task receipts, independent provisioning review and complete NEW current source/import/tool/archive/map readiness; no bootstrap alias, global dependency install, guard relaxation or implicit recovery/measurement/producer action.

Narrow proof: pinned `source004:provider:retain` (proposed name) performs only the
declared exact dependency provisioning/retention, with independently reviewed
saved recovery and provisioning receipts. It does not call root:prepare.
After5.6 and new whole current-tuple readiness, separately declare at most one
NEW sole-root read-only root:prepare whole-cost experiment under original165/300
with distinct start/output/actual terminal/failure paths and complete fresh
cost/content/ownership proof for5.4/5.5. All prior failures remain retained; hardware tasks
remain unchanged and unchecked; failure admits no automatic further follow-up.
Planning proof is only pinned Task patch-applicability and strict OpenSpec in a
copied tree; actual provisioning/recovery/measurement proof is still pending.

## 6. Correct timed receiver ownership before admission (UNVERIFIED)

This software prerequisite refines4.4 with a NEW private receiver/caller/support/
holder bundle. All prior bytes and physical tasks remain unchanged; exact scope
and the shared30-second cleanup clock are declared in
[design](design.md#timed-receiver-owned-cleanup-prerequisite-unverified).

- [ ] 6.1 Implement original spawn/member/pidfd authority and one shared absolute failure/aggregate cleanup deadline for source/monitor/UART workers and their members; keep coordinator/keeper forwarding and terminal join under their original bounds. Preserve original restoration/terminal ceilings, CID/name/image predicates, legacy/v1/native/old15 inputs and existing quarantine. Proof: complete changed-map/source comparison, no unsafe numeric signal, no per-child/cancellation renewal or uncertain FD-number retry, and explicit whole caller/holder terminal policy.
- [ ] 6.2 Replay all original receiver004 tests and the unchanged five-case probe, adding separately frozen real own-session/descendant and external subprocess normal/recovery/failure controls for missing/mutated/partial identity, reap, escaped/late members, modeled numeric reuse, FD ambiguity, clocks/cancellation, every role and keeper/pending/terminal effects. Proof: pinned private Task actual exits and complete immutable source/log/import/archive maps, retained failures and independent whole-chain review; no actual hardware/service/store/compiler operation.
- [ ] 6.3 Transfer and rehash the independently reviewed complete new host bundle at distinct root paths with a source-bound readiness receipt, retaining all old snapshots. Proof: byte-exact author/peer/root map join and missing-source-qualification operational-freeze refusal before runtime/archive queries or access. This host handoff cannot close4.4 or substitute for actual4.3 qualification, later current full runtime/admission proof or physical4.5/4.6.

Narrow proof: the new ignored bundle's explicit pinned Task host-fixture recipe
and independent whole caller/holder replay, followed by a sole-root byte-only
transfer/refusal experiment. No physical checkbox, registry or accepted RF
requirement is changed by this group.


## Architecture004 prerequisites within6.1–6.3 (UNVERIFIED; proposed only)

The [whole-chain prospective design](design.md#whole-chain-authority-architecture004-unverified-proposed-only)
replaces rejected architecture002 after independent prospective review. It adds
no checkbox or completed task. Before implementing6.1, freeze the reviewed
supported-kernel/ABI/resource/FD contract, exact unprivileged filter-install
protocol, every-root role/API/wait matrix, task/exec lineage state machine,
surviving-caller/keeper loss contract and terminal conservation barrier. Preserve
both prior proposals, the complete133-file failed review and all119 author files.
Primitive compatibility and original timing remain UNVERIFIED until genuine
harmless fixtures establish them; root read-only metadata is not that proof.

For6.1, implement only a NEW private managed holder-root fork/exec handle and
single __WALL event pump, two bootstrap/GO barriers with exact filter entry/
success proof, all direct and inherited helper role transactions, typed FD/
kernel-user-worker admission, append-only nonleader-exec retirement, and real
tracer/lease-loss refusal. Account initial Git/admission, all endpoint/controller,
keeper/replacement, caller, final/error/restore helpers and partial spawns before
workload. Preserve original keeper policy, trusted daemon/container separation,
all historical helper/native/firmware bytes, shared worker30 and original
restoration/terminal bounds. No observed-only authority or permanent refusal
can satisfy the required functional positive paths.

For6.2, retain all161 original assertions and the original five-case failing
probe byte-exact. Add separately named positive and negative controls for exact
unprivileged installation and filter mutation/stacking, every root and API wait
consumer, all resource creation/FD injection paths (including io_uring inherited
ring/SQPOLL and vhost hazards), syscall ABI/fallback compatibility, child-first
birth events and task-bound role spoof/duplicate/missing transactions,
CLONE_PARENT/non-SIGCHLD/vfork, nonleader exec de_thread, actual tracer death with
continued execution/in-flight birth and covered no-tracer syscall errors,
caller/keeper/channel/storage loss, partial spawn,
original identity/PIDFD_THREAD semantics, late members, consumed FD numbers,
unchanged clocks, cancellation, natural/forced closure and actual external
CLI0/failure. Tests distinguish modeling from genuine own-session OS results;
no real device/service/store/compiler/controller operation is included.

For6.3, transfer only after independent whole NEW source/import/kernel-profile/
filter/command/actual-log/archive review. Root copies and rehashes distinct paths,
retaining all old failures. Missing actualsource4.3 blocks operational freeze
before runtime/archive queries or devices; no dummy profile/admission substitutes.
Current full runtime/physical receiver4.4–4.6 remain separate unchecked gates.

Narrow prospective proof: the NEW ignored bundle's pinned private Task recipe
runs Git apply --check and strict OpenSpec validation in a copied planning tree,
with exact base/proposed byte maps and captured actual CLI results. These checks
prove syntax/applicability only. Implementation proof later uses explicit pinned
Task harmless whole-chain fixtures, complete immutable manifests/archives and
independent full replay; no successful planning check is a hardware claim.

For6.1/6.2, explicitly implement/test native internal kernel-entry/birth/
child-stop/profile/pidfd transactions separately from application logical-role
IPC. Freeze exact selected Git/Docker/Go/CGO/library source and finite ABI/flags/
exec/resource/signal profiles, original root/TID/TGID and deadlines. Narrow native
own-live-TGID self-signals need exact original target authority and sealed births/
exec through actual return; external cleanup retains original individual pidfd
rules and no unsafe numeric signal. Genuine no-endpoint selected-native positive
controls must exercise each required class alongside forbidden/unknown/reuse/
exec/cancellation/native-error controls. Immutable native bytes, all old tests,
F1–F7, current checked5.1–5.3/open5.4–5.5 and all physical gates remain unchanged.
No missing native IPC, blanket ancestry or permanent refusal substitutes.
