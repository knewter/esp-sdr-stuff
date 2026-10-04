## Context

See [proposal](proposal.md) for the problem and scope. The hardware identity is recorded separately from untested reception and transport behavior.

## Goals / Non-Goals

**Goals:** A defensible usable-range and relative-spectrum report for this board and antenna.

**Non-Goals:** No absolute dBm or sensitivity claim without calibration; no full 100–6000 MHz coverage claim.

## Decisions

Separate command/capture stability from RF validation. Offset the LO to check the DC artifact; vary gain to identify clipping. Use labeled finite captures for each filter setting.

The host records revisions/settings/results; firmware owns modem and memory access; an FPGA, if selected, owns only its explicitly measured transport/processing boundary.

## Risks / Trade-offs

Unknown antenna response and AGC can change relative readings. Strong sources may overload. Without a calibrated reference the result remains relative, not a metrology claim.

## Validation and decision

Three repeatable source-on/source-off pairs with known center frequencies; each claimed extra tuning point has an independently known signal and uncertainty.

Physical procedure: fixed source, fixed antenna placement, paired on/off captures, three repeats per condition. The existing capture and analysis tools consume saved manifests and CSV. Acceptance requires the known-source response and repeated observations.

Pilot trials decoded [four owned BLE packets](docs/evidence/ble-owned-decoding/README.md) and [one packet during the filter/gain trial](docs/evidence/ble-controls-decoding/README.md). These establish narrow channel-37 reception; they do not satisfy three-cycle repeatability, calibrated filter/gain behavior or extended tuning. A [physical Bluetooth monitor trial](docs/evidence/ble-dumpcap-source/README.md) now checks accepted source settings independently of the ESP decoder. Its unlimited advertising episode provides no counted-emission denominator.

## Visual plan

[Experiment flow and provenance](docs/design/the-spectrum-reveals-controlled-24ghz-signals/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.

## Fresh-control nulls and source reference

The [original-profile control](docs/evidence/ble-bluez-control-001/README.md)
and [known-10-bit control](docs/evidence/ble-bluez-control-002/README.md)
retain 1,251 and 997 valid waveforms with independently reproduced null
decodes. Both restore the complete original flash and boot. No source-count
or RF-repeatability gate closes.

A separately built native passive observer on this same board is the next
source-reference diagnostic; see the [prospective bounded protocol](docs/research/ble-next-trial.md).
It can establish current source reception through the supported Bluetooth
stack, without proving hidden-SDR demodulation or transmitted event counts.
Its own finite observer-only build, exact-owned-data filtering, baseline
preflight and full restoration need independent review before operation.
Keep foreign addresses/data private, no NVS erase or active scan/connection,
and no weakening of the existing SDR artifact allowlist or RF acceptance gates.

The first [native trial](docs/evidence/native-ble-source-reference-001/README.md)
delivered 1,160 matching reports but failed scan completion. Full original-flash
restoration and source/monitor cleanup pass independent review. The pinned SDK
omits GAP timer dispatch when both connection roles are disabled. A separately
versioned app must deliberately stop at 90 seconds, require successful public
cancel plus inactive discovery and identify that completion method explicitly.
The failed trial is not retrospectively accepted. After a fresh successful native
reference, [twenty fixed gain-state snapshots](docs/research/esp-gain-state-diagnostic.md)
can observe the manual-control bit without reapplying settings or claiming gain
calibration. Neither diagnostic satisfies SDR or transmitted-count requirements.

The independently reviewed [native v2 trial](docs/evidence/native-ble-source-reference-002/README.md)
now completes with 1,176 owned reports, explicit successful cancellation at
90.092830 seconds and full original restoration. The enabled
[gain diagnostic](docs/evidence/gain-state-diagnostic-001/README.md) completes
20 integrity-valid snapshots; all 41 queries observe bit23=1. It applies settings
once, controls no source and restores the complete original flash and reset boot.
This gives no queried mismatch in that run, without reading effective gain or
earlier control state. The two fresh SDR nulls remain unresolved, Trial B remains
withheld, and the original RF/count acceptance criteria and tasks stay unchanged.

The [native direct-source comparison](docs/evidence/native-direct-reference-002/README.md)
now completes six alternating MaxEvents 255/0 episodes with 363 owned reports.
Both settings have positive guarded native reception; every actual termination
still reports `0x3c/count0`. All source cleanup and full original restoration
verify. The earlier comparison remains failed. These native observations do
not close SDR repeatability or transmitted-count gates.

The next [receiver-register observation design](docs/research/receiver-register-observation.md)
has an offline implementation with actual-C synthetic MMIO and strict host
receipt tests and a separately guarded physical diagnostic. It observes bounded readback of the field
the firmware writes as its forced selector, alongside bit23 at acquisition
stages, with RAM buffering and diagnostics after payload delivery. A separate
reviewed diagnostic artifact and declared protocol are prerequisites. No live
analog gain interpretation, source-count qualification or weakening of the
existing SDR allowlist follows from this plan.

## Declared diagnostics for the unresolved SDR controls

The [paired DC-first replay](docs/research/ble-dc-first-replay.md) first compares
saved waveforms using a separately named raw-mean subtraction wrapper around
the unchanged decoder. All original inputs, blind search bounds, complete packet
windows, protected CRC24, exact owned AD and deduplication remain required.
Original null receipts remain unchanged. A corrected saved-data positive would
establish decoding of that waveform, without supplying a live trial, emitted
denominator, source cause or three-pair RF response.

The [register-observation protocol](docs/research/receiver-register-observation-protocol.md)
declares a separate ESP32REGOBS1 artifact, initial readback and four bounded
acquisition-stage observations per capture. It uses the existing fixed
MANUAL/48, 2401 MHz, requested 20 MHz, ten-bit/16 MS/s profile for 20 captures,
with an absolute 30-second worker deadline including UART startup and queries.
Gain and source settings are never repaired or reapplied. Typed diagnostic
receipts follow complete binary payloads; failed prefixes stay failed. Exact
source, actual-C acquisition tests, generated linker-map separation, separate
artifact guards and independent review precede any installation. Original
4 MiB preservation, exclusive UART groups and full reset-boot restoration stay
required. Neither observation is equated with calibrated analog gain or RF
reception, and none of these diagnostics closes the original RF/count gates.

The [actual waveform comparison](docs/evidence/ble-waveform-comparison/README.md)
and independent full numerical replay reproduce the original five verified
historical results and 2,248 fresh nulls. Fresh ten-bit code power differs
substantially from the historical matching-profile subset, and the old
preprocessing retains a coherent translated DC component. Neither association
establishes a physical cause or calibrated gain. The separately named
[DC-first paired replay](docs/evidence/ble-dc-first-replay-001/README.md),
[independently reproduced](docs/evidence/ble-dc-first-independent-review/README.md),
checks all 3,043 saved captures, recovers no fresh packets and loses three
historical eight-bit results. It is not adopted as the default decoder.
Original accepted packets, null receipts and all live RF/count gates remain
unchanged. Register observation continues as a separate measurement, without
assuming that gain readback will explain the ADC distributions.

The [independent register source review](docs/evidence/register-observation-source-review/README.md)
records the rejected parser cases and their actual-C corrections, strict failed
receipt guards, bounded worker tests and integrity checks of the stale first
build. That first build remains unapproved and is refused by the current guard.
The corrected source now measures complete observation-body cycles separately
from the MMIO read bracket and declares residual measurement overhead. The
separate supervisor requires original wire framing/CRC replay, saved IQ checks,
confirmed whole-group closure and full original restoration. A fresh build,
target disassembly and independent lifecycle/artifact review precede the
physical register observation. Those prerequisites now passed for the
[completed register run](docs/evidence/receiver-register-observation-002/README.md):
20 valid captures and 81 stages in 10.522101644 seconds, with selector 48 / bit23=1
at every sampled stage and full original-flash/reset-boot restoration.
Measured hook-body cycles and residual measurement limits are explicit.
The [first attempt](docs/evidence/receiver-register-observation-001/README.md)
remains failed because the supervisor applied a protocol line limit to startup
noise; its restoration and subsequent offline replay remain separately recorded.
These observations narrow sampled field inconsistency in those runs without
establishing effective analog gain, prior state or the cause of the fresh nulls.
Original RF and transmitted-count gates are unchanged.

## Next bounded diagnostics

The [guarded ON/OFF scalar audit](docs/evidence/ble-on-off-waveform-audit/README.md)
finds no repeated increase in the predeclared positive-offset band and retains OFF excursions;
pooled code-power differences do not establish source response. Decoder bounds
remain unchanged. The [counter research](docs/research/ble-source-counter-followup.md)
finds no legacy exemption in the published HCI rules. A separately reviewed
[source-only mode pair](docs/research/ble-mode-counter-protocol.md) compares legacy
and extended reporting with fixed five-second duration/MaxEvents 255. Auxiliary
extended AD is outside this ESP32's native reference and channel-37 decoder.
This diagnostic cannot supply legacy marker counts or close RF/burst gates.

The [matched ten-bit gain protocol](docs/research/ble-matched-gain-protocol.md)
declares two fresh MANUAL48/HARDWARE controls with fixed bandwidth, precision,
artifact and three ON/OFF episodes per condition. Exact profile and lifecycle
review precedes hardware. Fixed-order restart and interference confounds remain;
requested software mode is not calibrated analog gain. Original RF/count gates
and the fresh hidden-SDR prerequisite for Trial B remain unchanged.

The [actual single mode pair](docs/evidence/ble-mode-counter-001/README.md)
now completes in 32.826581557 seconds with accepted commands and verified
source/monitor/group cleanup. Both modes retain `0x3c/count0`; the proposed
mode-associated distinction was not observed. Each helper retains its strict
failed count gate. No emitted denominator or hidden-SDR reception follows.

The [completed matched gain controls](docs/evidence/ble-matched-gain-001/README.md)
retain 1,010 manual48 and 984 hardware-gain snapshots. Independent full replay
and separate waveform re-slicing verify one fresh complete owned packet in
manual ON0; hardware has zero owned and one foreign CRC-valid packet, redacted.
Both full original restorations pass. Frozen positive-offset-band edges do not give
three reciprocal source responses. This reproduces a fresh ten-bit SDR example
without establishing calibrated gain, counts or the original eight-bit/BW12/
hardware-gain Trial B prerequisite. All original tasks remain unchanged.

The separately declared [single 100-event source-only diagnostic](docs/research/ble-count-limit-100-protocol.md)
keeps the five-second duration and legacy profile while changing only the
requested event limit from 255 to 100. The earlier 255-event limit needs at least
5.08 seconds between first/last starts at 20 ms, so that profile cannot normally
reach its count gate before duration expires. This does not explain the earlier
duration-zero failures or nonzero-limit zero reports. Independent preflight and
actual matching `0x43/count100` records are required for this diagnostic alone;
no emitted RF denominator, original 255-event qualification, RF response, or
Trial B prerequisite follows automatically. All task criteria stay unchanged.

The [actual legacy100 episode](docs/evidence/ble-count-limit-100-001/README.md)
also reports `0x3c/count0`, with five accepted commands, 22 unchanged frozen
inputs and independently verified full cleanup. Timing mismatch alone is not
the explanation. The next distinct [matched extended100 condition](docs/research/ble-extended-count-limit-100-protocol.md)
changes mode while keeping a reachable count limit. It requires separate frozen
review and strict actual source/monitor `0x43/count100` agreement; extended
auxiliary AD cannot supply the original channel-37 marker denominator. No
original gate changes and no identical legacy retry follows.

The [actual extended100 episode](docs/evidence/ble-extended-count-limit-100-001/README.md)
now records matching `0x43/count100` and source exit0, distinguishing it from
legacy100. Its monitor hits the host deadline and the complete protocol correctly
fails with parent exit2, despite all retained commands and cleanup matching.
[Independent replay](docs/evidence/ble-extended-count-limit-100-independent-review/actual-001-review.md)
accepts that distinction and reproduces startup consuming a shared deadline
offline. Separate bounded readiness/capture clocks need review before any
fresh operation. The auxiliary-mode report does not give a legacy marker
denominator or close an original RF/burst gate.

The [explicit monitor timer option](docs/research/ble-monitor-readiness-timing.md)
now has 26 offline subprocess/parser/cleanup tests. The
[independent timer review](docs/evidence/ble-monitor-readiness-independent-review/README.md)
also verifies ten checks, including rejection of a delayed EOF beyond the
absolute bound. Existing default timing and
the failed actual receipts remain unchanged. A separate frozen protocol and
independent review are needed before using it in any new physical episode.

## Final original ladder outcome

The [final original BW12 control](docs/evidence/ble-bluez-control-007/README.md) completes the prospective ladder: all 1,151 captures, whole decoder/scalar replay, source schedule, cleanup and full restoration pass independent audit. Zero CRC-valid packets and no repeated owned-source nominal-band rise supply no emitted-event denominator or detection/miss rate. Original Trial B remains withheld; neither radio acceptance gate is relaxed.
