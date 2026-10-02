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
