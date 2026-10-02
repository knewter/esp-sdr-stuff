## Purpose

Decide which interference, educational DSP and short-burst applications are useful on this board.

## ADDED Requirements

### Requirement: Event detection has ground truth

The evaluation SHALL report observed and missed controlled events against a recorded source count.

<!-- UNVERIFIED: Five owned packets decode, but no usable recorded source denominator exists. Three initial finite source-only HCI trials had no termination; subsequent timer diagnostics report an actual zero field, and a 262-snapshot RF discriminator is inconclusive. Requested limits and the unvalidated zero field do not establish emitted-event counts. Hit rates and unresolved misses/truncations remain unknown. See docs/evidence/ble-counted-source-smoke/README.md and docs/evidence/ble-zero-counter-rf/README.md. -->

#### Scenario: Evaluation result is inspected
- **WHEN** event detection is assessed
- **THEN** hit rate includes missed windows and truncated events

### Requirement: Decoding claims include payload verification

The report SHALL label decoding demonstrated only when a complete capture yields the independently known payload.

*Grounding: [actual protected-PDU CRC and exact known-marker verification](docs/evidence/ble-owned-decoding/README.md) records four complete captured packets, private input hashes, bounded blind decoder revision and payload comparison; [10-bit control example](docs/evidence/ble-controls-decoding/README.md) adds a fifth packet. Preamble/access hard-decision errors remain explicit and outside the protected CRC.*

#### Scenario: Evaluation result is inspected
- **WHEN** a decoding capability is reported
- **THEN** the waveform, decoder revision and payload comparison are available
