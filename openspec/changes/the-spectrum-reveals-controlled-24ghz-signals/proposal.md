## Why

A plausible waterfall could show aliases or internal noise. We need controlled signals to learn usable bandwidth, tuning accuracy and overload behavior.

## What Changes

- Observe known 2.4 GHz sources, then compare source-on/source-off captures.
- Measure frequency offset, filter shape, DC artifacts, clipping and gain repeatability.
- Probe extended tuning only where a known source or independent reference can establish real reception.

## Capabilities

### New Capabilities

- `radio/rf-characterization`: A defensible usable-range and relative-spectrum report for this board and antenna.

### Modified Capabilities

None. Existing identity records remain factual baselines.

## Impact

Physical ESP32 plus an owned Wi-Fi/BLE source; calibrated RF source/reference and attenuators for stronger measurements, if available.

Dependencies: [the board captures repeatable radio snapshots](../the-board-captures-repeatable-radio-snapshots/proposal.md)

## Non-goals

No absolute dBm or sensitivity claim without calibration; no full 100–6000 MHz coverage claim.

## Decision gate

Three repeatable source-on/source-off pairs with known center frequencies; each claimed extra tuning point has an independently known signal and uncertainty.

## Evidence and sources

Baseline: [research](docs/research/source-index.md). Sources: [primary-source register](docs/research/source-index.md).
