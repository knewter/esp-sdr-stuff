## Purpose

A recovery route that restores the observed GPIO test with clearly identified backup provenance.

## ADDED Requirements

### Requirement: Firmware preservation is complete

The evaluation SHALL retain a private full-flash backup and a public size/hash record before installing experimental firmware.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** a trial is scheduled
- **THEN** the preservation manifest identifies a complete 4 MiB image without exposing its contents

### Requirement: Restoration has physical proof

The evaluation SHALL retain a fresh boot proving the baseline image is restored after a trial.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** the original image is restored
- **THEN** the recorded application behavior matches the captured baseline
