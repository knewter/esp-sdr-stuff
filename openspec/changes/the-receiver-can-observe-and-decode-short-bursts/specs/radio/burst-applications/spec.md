## Purpose

Decide which interference, educational DSP and short-burst applications are useful on this board.

## ADDED Requirements

### Requirement: Event detection has ground truth

The evaluation SHALL report observed and missed controlled events against a recorded source count.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** event detection is assessed
- **THEN** hit rate includes missed windows and truncated events

### Requirement: Decoding claims include payload verification

The report SHALL label decoding demonstrated only when a complete capture yields the independently known payload.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** a decoding capability is reported
- **THEN** the waveform, decoder revision and payload comparison are available
