## Why

Seeing activity is useful but does not establish packet decoding or reliable event detection. We need an honest application shortlist based on finite capture windows.

## What Changes

- Evaluate channel occupancy and repeated-burst detection on an owned controlled source.
- Try offline demodulation of complete short bursts that fit captured windows.
- Report hit rate, decode rate and missed windows separately from spectrum visibility.

## Capabilities

### New Capabilities

- `radio/burst-applications`: Decide which interference, educational DSP and short-burst applications are useful on this board.

### Modified Capabilities

None. Existing identity records remain factual baselines.

## Impact

Physical ESP32 and owned repeatable Wi-Fi/BLE or simple 2.4 GHz test waveform. Protocol-generator hardware depends on inventory.

Dependencies: [the board captures repeatable radio snapshots](../archive/2026-10-01-the-board-captures-repeatable-radio-snapshots/proposal.md), [the spectrum reveals controlled 24ghz signals](../the-spectrum-reveals-controlled-24ghz-signals/proposal.md)

## Non-goals

No whole-session Bluetooth capture, guaranteed packet logging, continuous audio or encrypted-content access.

## Decision gate

At least 100 deliberately emitted repeat events with ground-truth counts and capture hit rate; a decoding claim includes a complete waveform and verified payload.

## Evidence and sources

Baseline: [research](docs/research/source-index.md). Sources: [primary-source register](docs/research/source-index.md).
