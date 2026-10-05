## Purpose

Decide which interference, educational DSP and short-burst applications are useful on this board.

## ADDED Requirements

### Requirement: Event detection has ground truth

The evaluation SHALL report observed and missed controlled events against a recorded source count.

<!-- UNVERIFIED: Five owned packets decode, but no usable recorded source denominator exists. Three initial finite source-only HCI trials had no termination; subsequent timer diagnostics report an actual zero field, and a 262-snapshot RF discriminator is inconclusive. Requested limits and the unvalidated zero field do not establish emitted-event counts. Hit rates and unresolved misses/truncations remain unknown. See docs/evidence/ble-counted-source-smoke/README.md and docs/evidence/ble-zero-counter-rf/README.md. -->

#### Scenario: Evaluation result is inspected
- **WHEN** event detection is assessed
- **THEN** hit rate includes missed windows and truncated events

### Requirement: Decoding claims include payload verification

The report SHALL label decoding demonstrated only when a complete capture yields the independently known payload.

*Grounding: [actual protected-PDU CRC and exact known-marker verification](docs/evidence/ble-owned-decoding/README.md) records four complete captured packets, private input hashes, bounded blind decoder revision and payload comparison; [10-bit control example](docs/evidence/ble-controls-decoding/README.md) adds a fifth packet. Preamble/access hard-decision errors remain explicit and outside the protected CRC.*

#### Scenario: Evaluation result is inspected
- **WHEN** a decoding capability is reported
- **THEN** the waveform, decoder revision and payload comparison are available

### Requirement: Longer primary diagnostics retain separate qualification and opportunity units

The evaluation SHALL keep a separately timed zero-data primary diagnostic's
source qualification, acquisition-window coverage and observations distinct
from counted v1 controller events, independently emitted RF events and the
original acceptance gates.

<!-- UNVERIFIED: Timed-v2 source and built archive pass offline independent review in docs/evidence/ble-primary-timed-source-host-preparation/README.md; caller admission, physical source qualification and the new receiver/holder remain unverified. The completed fixed receiver001 has11 guarded ON windows and no CRC-valid primary; see docs/evidence/ble-primary-zero-data-receiver-001-review/README.md. Prospective fields, ownership, clocks and proof gates are in docs/research/ble-primary-timed-zero-data-v2-protocol.md. -->

#### Scenario: A timed source condition is admitted
- **WHEN** a longer timer-limited primary condition is proposed after the fixed diagnostic
- **THEN** its exact finite profile, observed timer status and complete cleanup receive independent source-only qualification before receiver action
- **AND** v1 source/image/guard and previous frozen private inputs remain unchanged

#### Scenario: Longer diagnostic coverage is reported
- **WHEN** the timed condition's saved source and receiver records are reviewed
- **THEN** the report counts whole guarded ON acquisition windows per repetition and retains every OFF, boundary, sparse and failed outcome
- **AND** a completed-count byte, requested duration or window threshold does not establish an air denominator, event rate, three reciprocal RF responses or original Trial B acceptance

#### Scenario: Verification cost requires new preparation
- **WHEN** source003 full verification refuses the existing timed-source admission budget
- **THEN** a separately reviewed source004 and outer gate SHALL retain every fresh local byte/import/reference/NAR/archive predicate and complete worker ownership within unchanged source45/caller30/native32/whole165/outer300 bounds
- **AND** hermetic pinned selection and exact locked public input retrieval occur only before monitor; no selector, fetch or build occurs inside45
- **AND** neither architecture review nor a parallel allocation estimate admits a source or closes any physical acceptance gate

<!-- UNVERIFIED: source004 is prospective only; actual source003 cost/refusal is retained in docs/evidence/ble-primary-timed-startup-preparation-review/README.md. The independently reviewed design prerequisite and private provenance pins are in this change's design.md. Actual current tuple, complete timing, source and receiver qualification remain pending. -->

#### Scenario: Complete verification exceeds the source budget
- **WHEN** a saved complete read-only preparation is too slow for timed admission
- **THEN** a separately identified bounded measurement evaluation SHALL retain every original fresh proof, ownership and deadline predicate and distinguish measured operation brackets from inferred costs
- **AND** complete current-tuple timing and independent review precede any separately planned optimization or source qualification
- **AND** a partial compatible proof, reduced input set, cached content result or clock extension cannot establish fit

<!-- UNVERIFIED: The accepted historical source004 read-only proof in docs/evidence/ble-primary-timed-source004-readonly-review/README.md is not source45 timing. Saved-ledger decomposition and the corrected003 cancellation-only baseline are pinned separately in design.md. Instrumentation, actual current-tuple costs and fit remain prospective; all physical tasks and original air/count/reception gates remain open. -->

### Requirement: Timed receiver teardown retains original ownership

The NEW private timed receiver/caller/holder chain SHALL retain original spawn
and complete member identity with individual pidfds independently of mutable
receipts. It SHALL NOT signal an unqualified numeric PID/PGID or infer complete
closure from one leader. All failed-child/aggregate source/monitor/UART worker
and member cleanup SHALL share
one absolute deadline set once at first cleanup to the minimum of original
caller deadline, entry plus30 seconds and holder first-cancel plus1800 seconds
when present. Every cleanup persistence/descriptor effect SHALL remain charged;
per-child work or repeated cancellation SHALL NOT renew it. Full restoration
and holder finalization SHALL retain original5400/first-cancel1800 ceilings.
Lifecycle caller/holder coordinators, keeper and their terminal join SHALL remain
under those original ceilings; no renewed30-second clock or forced coordinator
kill during unresolved restoration SHALL follow the shorter worker cleanup.
Unknown ownership SHALL retain existing pending/keeper/quarantine refusal and
prohibit restoration or further endpoint actions.

<!-- UNVERIFIED: Five unchanged saved-source probes in independent receipt b992ff26c9ecb0ee9446c31a43819fa1042c65a3800a56e19af6cad36dc0c4e9 reproduce unqualified legacy stop decisions in six harmless owned sessions, with signals/reuse modeled. Correction, whole holder review and new root handoff remain pending. No foreign kill or physical operation was observed; see this change's design.md for the prospective scope. -->

#### Scenario: Child ownership cannot be established
- **WHEN** original identity, retained member/pidfd authority or complete membership is missing, changed or ambiguous, including reaped-leader ambiguity, during any source/monitor/UART or holder cleanup
- **THEN** no unsafe numeric signal or descriptor retry occurs, natural closure remains unqualified and existing refusal blocks restoration and endpoint access

#### Scenario: Teardown completes normally
- **WHEN** actual exit0, all owned-member absence, durable logs, exact descriptor closure and complete caller/holder terminal handoff finish within the original bounds
- **THEN** independently observed CLI and saved whole-chain proof may qualify only host preparation; actual source4.3 and fresh full root runtime/admission proof still precede receiver action
- **AND** ordinary natural exit0 reaping with complete retained member authority is distinct from ambiguous leader-only absence


<!-- UNVERIFIED: Root cost003 failed Task201/prepare2 after six natural selection
closures and absent exact qfwk7cy provider; all43 files remain preserved.
Separately qualified administrative recovery, exact dependency retention and
current readiness now pass; actual cost004 retains content/natural-terminal
proof but fails cost completeness with five completed records missing. See
docs/evidence/source004-actual-readonly-cost-004/README.md. Original failures and
unproven historical marker creation-inode authority remain unchanged. Recording
correction and whole measurement qualification stay pending. This proposed delta
changes neither accepted specs nor source/receiver/physical admission. -->

#### Scenario: Exact selected provider is absent before whole cost measurement
- **WHEN** pure locked-flake selection returns a provider output that is absent or fails exact identity
- **THEN** the whole attempt SHALL retain its failed prefix, actual terminal, pending/keeper and complete named saved artifacts without substituting bootstrap or an equal-version binary
- **AND** independently qualified recovery SHALL precede new operation admission; provider provisioning SHALL use a separately reviewed locked-flake Task and registered persistent ignored GC root outside measurement, with no guard or original clock change
- **AND** provisioning SHALL NOT imply fresh content proof, keeper release, producer action or an automatic measurement retry

#### Scenario: A new read-only cost follow-up is declared
- **WHEN** qualified recovery, exact provider provisioning/retention review and complete current source/map/archive readiness have all passed independently
- **THEN** the sole operator MAY declare at most one NEW read-only whole-cost follow-up under the unchanged165/300 clocks with distinct command/tuple/output/terminal/failure receipts
- **AND** every original fresh reference/NAR/archive/import/content, worker/keeper/FD/cost/terminal predicate SHALL remain required; cached provisioning outputs SHALL NOT replace fresh proof
- **AND** failed/partial/late/unknown-ownership results SHALL remain failures without another automatic follow-up, and all source4.3, receiver and physical gates SHALL remain unchanged


<!-- UNVERIFIED: Architecture004 replaces the rejected prospective002 design only
after independent planning review. Exact supported-kernel primitive/resource
compatibility, full new-chain implementation and all physical gates remain open.
Historical161 assertions and the literal failing ownership probe are unchanged.
This proposed delta does not alter openspec/specs/. -->

#### Scenario: Exact filter and every holder root precede workload
- **WHEN** the NEW timed chain spawns any caller, keeper, replacement keeper, Git, endpoint, controller, postflight or cleanup root
- **THEN** original partial-spawn PID/pidfd authority SHALL be retained before fallible effects, and a stopped pre-install bootstrap plus sole-tracer immutable exact filter entry/success join SHALL precede READY and role/deadline-bound GO
- **AND** the unprivileged protocol SHALL NOT rely on CAP_SYS_ADMIN GET_FILTER, undeclared stacked filters, JSON-only proof or Popen preexec/convenience wait behavior
- **AND** one holder event pump SHALL own all tracer waits; real-parent terminal joins SHALL remain distinct from stops, ECHILD, body markers and EXIT notifications

#### Scenario: A supported workload could create an untraced kernel user worker
- **WHEN** a kernel/ABI/syscall/device/ioctl or inherited/received FD resource permits user-worker creation outside ordinary ptrace birth events
- **THEN** a complete pinned supported-kernel creation-path and FD-provenance contract SHALL either exclude that path before effect or provide original complete authority before work
- **AND** io_uring APIs, inherited/transferred/mapped rings and SQPOLL resources plus vhost-triggering resources SHALL be excluded; clone flags or setup-only denial SHALL NOT qualify complete coverage
- **AND** required normal runtime, controller and UART operation SHALL have positive proof under the finite typed profile; unknown paths SHALL NOT turn an always-refusing placeholder into readiness

#### Scenario: Nonleader exec transfers the logical process lineage
- **WHEN** de_thread retires a former TID or exchanges kernel PID identity during traced exec
- **THEN** append-only task birth and logical process histories SHALL join the actual former-TID exec event and stopped survivor to typed retirement/transfer, retaining immutable role and original deadline
- **AND** old signal bindings SHALL be retired and current survivor pidfd authority SHALL be reconciled before action; an impossible ordinary former-TID death SHALL NOT be demanded
- **AND** actual surviving-process terminal and complete task-history conservation SHALL remain required

#### Scenario: Real tracer or lease actor is lost
- **WHEN** holder/tracer death automatically detaches/resumes tasks, or caller/channel/keeper/storage authority is lost
- **THEN** surviving caller and existing keeper SHALL retain the declared loss/refusal behavior, with no new endpoint/restoration/release decision from incomplete authority and no reconstructed membership
- **AND** actual detach/resume SHALL NOT be described as a frozen tree; conditional no-tracer errors for installed covered RET_TRACE calls SHALL NOT establish complete closure, existing keeper EOF/release policy SHALL remain unchanged, and unresolved restoration SHALL NOT be forcibly killed under worker30 or EXITKILL
- **AND** destruction of every trusted lease actor SHALL be an explicit host limit and SHALL NOT create a lock-retention or completed-CLI claim

#### Scenario: Whole-chain completion is proposed
- **WHEN** the new caller/holder chain proposes restoration or release
- **THEN** actual parent/child birth events, stopped newborns, task-bound role transactions, exec transfers, resources, real-parent waits and charged FD/log effects SHALL reconcile in a sealed no-live-worker-birth-source frontier
- **AND** actual coordinator stops and event/request joins SHALL seal the worker GO epoch before closure; later finalization helpers SHALL register in a separate frontier, and undeclared late workers SHALL remain stopped and fail the handoff
- **AND** child-first ordering, CLONE_PARENT, reparenting, late births, duplicates or missing events SHALL NOT disappear through an empty table, WNOHANG0 or leader reap
- **AND** original container/OFF/ACK/absence predicates, restore helper closure, keeper/root FD/marker effects and actual holder/external CLI terminal SHALL join under unchanged clocks before host qualification

<!-- UNVERIFIED: Native internal kernel transaction and narrow self-signal
contracts are prospective004 clarifications after peer034 failure. Exact patched
selected runtime, supported kernel, functionality and timing remain unproved. -->

#### Scenario: An immutable native runtime creates an internal member
- **WHEN** an admitted unchanged Git/Docker/Go/CGO/native root creates a thread or predeclared internal helper without application role IPC
- **THEN** the sole holder SHALL join exact original root/calling TID/TGID/pidfd/profile/ABI/flags and kernel entry/birth/child-stop/exec/resource transactions before resume, retaining original role and absolute deadline
- **AND** new logical roles/endpoints/restoration SHALL still require authenticated application IPC; unknown native ancestry or missing kernel transactions SHALL remain stopped/failed rather than blanket-admitted or permanently refusing required positives

#### Scenario: A native runtime issues a self-signal
- **WHEN** a native signal call is captured at kernel entry before effect
- **THEN** finite source/signal semantics, current original issuing group, exact retained live target pidfd/member authority and a sealed birth/exec frontier through actual return SHALL establish any narrowly allowed self operation
- **AND** own-group tgkill, positive own-TGID kill or exact issuing-TID tkill SHALL NOT permit a foreign/unknown/reused target, peer-TID tkill, numeric group kill, role transition or broader external cleanup
- **AND** the original no unsafe numeric signal requirement and external individual-pidfd cleanup policy SHALL remain, with genuine native positive/error/refusal controls and original clocks required before readiness
