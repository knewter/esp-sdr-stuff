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
