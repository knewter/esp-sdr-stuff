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

Physical procedure: fixed source, fixed antenna placement, paired on/off captures, three repeats per condition. Future plot harness consumes the saved capture manifest and CSV; raw acceptance is based on the known-source shift and repeated response, not just an OK command.

## Visual plan

[Experiment flow and provenance](docs/design/the-spectrum-reveals-controlled-24ghz-signals/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.
