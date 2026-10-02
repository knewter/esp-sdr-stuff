## Context

See [proposal](proposal.md) for the problem and scope. The hardware identity is recorded separately from untested reception and transport behavior.

## Goals / Non-Goals

**Goals:** A receiver-by-application decision matrix grounded in this host and these two units.

**Non-Goals:** No direct 2.4 GHz reception claim for V4; no cross-band sensitivity ranking from unrelated antennas; no installed continuous ESP stream claim.

## Decisions

Use V4 for continuous narrowband HF/VHF/UHF reception and the ESP for 2.4 GHz snapshots. Their direct tuning bands do not overlap in the normal supported configurations; use converter-assisted tests only when that hardware is present. eSpDR with S3/FPGA is a separate candidate, not this board upgraded by USB.

The host records revisions/settings/results; firmware owns modem and memory access; an FPGA, if selected, owns only its explicitly measured transport/processing boundary.

## Risks / Trade-offs

V4 tuner identification and this selected FM/RDS application are proven; calibrated RF performance remains unmeasured. A configured rate is not sustained delivery. RF sensitivity comparisons need the same calibrated signal path.

## Validation and decision

At least 60 seconds per V4 sample rate with lost-sample counts, plus measured ESP snapshot gaps. Each chosen application states the receiver, coverage, continuity and proof status.

V4 stream procedure: `timeout --signal=INT 60s rtl_test -s RATE`, one device owner at a time, all stdout/stderr retained. Use rates 1024000, 2048000, 2400000 and 2560000; timeout termination is expected, not a tuner failure. RF and ESP comparison uses their saved manifests.

## Visual plan

[Experiment flow and provenance](docs/design/the-two-receivers-have-a-measured-division-of-labor/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.

## Observed progress

[V4 transport evidence](docs/evidence/rtl-continuity/README.md) now records all
four requested rates for at least 65 seconds each. The measurement uses internal
test bytes, so it proves the named transport trial rather than tuning range,
calibrated bandwidth, antenna suitability or reception. The ten-second rate
estimates depend on host/USB timing and are not calibrated oscillator results.

[Passive FM discovery](docs/evidence/rtl-fm-survey/README.md) initially
recorded an unidentified candidate. [Fresh current-dipole RDS](docs/evidence/rtl-dipole-rds/README.md)
now identifies WXJC at 101.1 MHz with FEC disabled; [independent replay](docs/evidence/rtl-dipole-independent-review/README.md)
accepts the selected known-source application. The user's current dipole works
for this station; its geometry and other-band performance remain unverified.

The user reports no external RF equipment in the [equipment inventory](docs/evidence/user-equipment-inventory/README.md).
The common calibrated ESP/converter sensitivity comparison is deferred under
the original task's absent-equipment branch. No RF sensitivity ranking is inferred.
