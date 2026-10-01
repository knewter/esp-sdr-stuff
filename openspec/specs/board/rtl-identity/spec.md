## Purpose

Identify the existing USB SDR precisely so comparisons use its real tuner and driver behavior.

## Requirements

### Requirement: Attached RTL receiver is identified
The project SHALL retain a direct tuner probe that identifies the attached RTL-SDR Blog V4 and R828D.

*Grounding: `docs/evidence/rtl-identification/README.md` and `docs/evidence/rtl-identification/tuner.log` record the direct driver probe.*

#### Scenario: Reader checks the existing SDR
- **WHEN** a reader opens the tuner record
- **THEN** Blog V4 and Rafael Micro R828D are visible, with the E4000-test limitation explained
