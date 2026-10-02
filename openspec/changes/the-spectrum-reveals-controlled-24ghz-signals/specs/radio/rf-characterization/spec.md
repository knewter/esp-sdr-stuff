## Purpose

A defensible usable-range and relative-spectrum report for this board and antenna.

## ADDED Requirements

### Requirement: Reception claims use controlled signals

The report SHALL support each usable-band claim with a known source or independent reference and repeated observations.

<!-- UNVERIFIED: Physical trials decoded five owned BLE packets at channel 37, but three repeated source-on/off responses and evidence for each usable-band claim remain incomplete. See docs/evidence/ble-owned-decoding/README.md and docs/evidence/ble-controls-decoding/README.md. -->

#### Scenario: Evaluation result is inspected
- **WHEN** a tuning interval is claimed usable
- **THEN** the source frequencies and receiver response evidence are available

### Requirement: Measurement uncertainty is explicit

The report SHALL distinguish relative power, frequency uncertainty, clipping and calibrated measurements.

<!-- UNVERIFIED: Physical filter/gain trials and explicit calibration limits are recorded, but repeatable input, filter shape, frequency uncertainty and clipping characterization remain incomplete. See docs/evidence/rf-controls-trial/README.md. -->

#### Scenario: Evaluation result is inspected
- **WHEN** a reader inspects a spectrum result
- **THEN** calibration limits and source/receiver settings are visible
