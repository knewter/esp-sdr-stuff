## Purpose

Decide which interference, educational DSP and short-burst applications are useful on this board.

## ADDED Requirements

### Requirement: Event detection has ground truth

The evaluation SHALL report observed and missed controlled events against a recorded source count.

*Grounding: [pre-declared run 002](docs/evidence/ble-receiver-hitrate-002/README.md) reports 42 complete owned packets in 3,188 ON / 0 in 111 OFF windows against 48,450 controller-counted events, with expected in-window, truncated and acquisition-missed events and a 95% interval (0.28–0.52). The denominator is controller-completed events, not independently observed air emissions; [run 001](docs/evidence/ble-receiver-hitrate-001/README.md) is the retained post-hoc diagnostic.*

#### Scenario: Evaluation result is inspected
- **WHEN** event detection is assessed
- **THEN** hit rate includes missed windows and truncated events

### Requirement: Decoding claims include payload verification

The report SHALL label decoding demonstrated only when a complete capture yields the independently known payload.

*Grounding: [actual protected-PDU CRC and exact known-marker verification](docs/evidence/ble-owned-decoding/README.md) records four complete captured packets, private input hashes, bounded blind decoder revision and payload comparison; [10-bit control example](docs/evidence/ble-controls-decoding/README.md) adds a fifth packet. Preamble/access hard-decision errors remain explicit and outside the protected CRC.*

#### Scenario: Evaluation result is inspected
- **WHEN** a decoding capability is reported
- **THEN** the waveform, decoder revision and payload comparison are available
