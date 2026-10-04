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
