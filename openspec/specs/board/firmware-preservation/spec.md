# Firmware preservation Specification

## Purpose

A recovery route that restores the observed GPIO test with clearly identified backup provenance.

## Requirements

### Requirement: Firmware preservation is complete

The evaluation SHALL retain a private full-flash backup and a public size/hash record before installing experimental firmware.

*Grounding: [two complete matching physical flash reads and security/partition records](docs/evidence/firmware-preservation/README.md) identify the private 4,194,304-byte image before experimental SDR installation; [independent recovery review](docs/evidence/power-cycle-recovery-review/README.md) rechecks its hash and private-only retention.*

#### Scenario: Evaluation result is inspected
- **WHEN** a trial is scheduled
- **THEN** the preservation manifest identifies a complete 4 MiB image without exposing its contents

### Requirement: Restoration has physical proof

The evaluation SHALL retain a fresh boot proving the baseline image is restored after a trial.

*Grounding: [full original-image restore and independent 4 MiB readback](docs/evidence/zero-counter-restoration/README.md), [user-reported power removal/reapplication followed by a matching original application boot](docs/evidence/user-power-cycle-recovery/README.md), and [independent review](docs/evidence/power-cycle-recovery-review/README.md) establish recovery for the preserved baseline. UART opening may cause an additional reset; neither precise cold-edge timing nor electrical rail measurement is claimed.*

#### Scenario: Evaluation result is inspected
- **WHEN** the original image is restored
- **THEN** the recorded application behavior matches the captured baseline
