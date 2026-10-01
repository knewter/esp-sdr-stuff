## Context

See [proposal](proposal.md) for the problem and scope. The hardware identity is recorded separately from untested reception and transport behavior.

## Goals / Non-Goals

**Goals:** A receiver-by-application decision matrix grounded in this host and these two units.

**Non-Goals:** No direct 2.4 GHz reception claim for V4; no cross-band sensitivity ranking from unrelated antennas; no installed continuous ESP stream claim.

## Decisions

Use V4 for continuous narrowband HF/VHF/UHF reception and the ESP for 2.4 GHz snapshots. Their direct tuning bands do not overlap in the normal supported configurations; use converter-assisted tests only when that hardware is present. eSpDR with S3/FPGA is a separate candidate, not this board upgraded by USB.

The host records revisions/settings/results; firmware owns modem and memory access; an FPGA, if selected, owns only its explicitly measured transport/processing boundary.

## Risks / Trade-offs

V4 tuner identification is proven, but capture quality is not. A configured rate is not sustained delivery. RF sensitivity comparisons need the same calibrated signal path.

## Validation and decision

At least 60 seconds per V4 sample rate with lost-sample counts, plus measured ESP snapshot gaps. Each chosen application states the receiver, coverage, continuity and proof status.

V4 stream procedure: `timeout --signal=INT 60s rtl_test -s RATE`, one device owner at a time, all stdout/stderr retained. Use rates 1024000, 2048000, 2400000 and 2560000; timeout termination is expected, not a tuner failure. RF and ESP comparison uses their saved manifests.

## Visual plan

[Experiment flow and provenance](docs/design/the-two-receivers-have-a-measured-division-of-labor/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.
