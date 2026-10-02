## Why

The existing Blog V4 and the ESP32 offer different frequency coverage and continuity. We need a measured division of labor so the new experiment adds capability instead of duplicating the working receiver.

## What Changes

- Measure the Blog V4 USB sample-loss envelope and document its HF-to-UHF application coverage.
- Compare delivered sample continuity and usable bandwidth with the ESP32 baseline.
- Define optional same-signal tests through external frequency conversion, with mixer/LO losses and calibration recorded.

## Capabilities

### New Capabilities

- `radio/receiver-comparison`: A receiver-by-application decision matrix grounded in this host and these two units.

### Modified Capabilities

None. Existing identity records remain factual baselines.

## Impact

Attached RTL-SDR Blog V4/R828D, original ESP32, appropriate antennas and controlled sources. A same-signal RF comparison additionally needs a converter/reference; the user reports no external RF equipment, so that optional comparison is deferred.

Dependencies: [the board captures repeatable radio snapshots](../2026-10-01-the-board-captures-repeatable-radio-snapshots/proposal.md), [the spectrum reveals controlled 24ghz signals](../../the-spectrum-reveals-controlled-24ghz-signals/proposal.md)

## Non-goals

No direct 2.4 GHz reception claim for V4; no cross-band sensitivity ranking from unrelated antennas; no installed continuous ESP stream claim.

## Decision gate

At least 60 seconds per V4 sample rate with lost-sample counts, plus measured ESP snapshot gaps. Each chosen application states the receiver, coverage, continuity and proof status.

## Evidence and sources

Baseline: [rtl-identification](docs/evidence/rtl-identification/README.md). Sources: [primary-source register](docs/research/source-index.md).
