# Receiver comparison Specification

## Purpose

A receiver-by-application decision matrix grounded in this host and these two units.

## Requirements

### Requirement: Receiver recommendations state coverage and continuity

The report SHALL distinguish V4 direct HF-to-UHF coverage from ESP32 2.4 GHz snapshots with measured continuity limits.

*Grounding: [V4 transport](docs/evidence/rtl-continuity/README.md), [ESP snapshot timing](docs/evidence/snapshot-baseline/README.md), [fresh current-dipole RDS](docs/evidence/rtl-dipole-rds/README.md), [measured recommendations](docs/research/measured-recommendations.md) and [independent review](docs/evidence/rtl-dipole-independent-review/README.md).*

#### Scenario: Evaluation result is inspected
- **WHEN** a reader chooses a receiver for an application
- **THEN** its tuning limits, gap behavior and evidence status are visible

### Requirement: Same-signal comparisons identify conversion hardware

The evaluation SHALL require a documented common signal path before comparing RF sensitivity across disjoint receiver bands.

*Grounding: [User equipment inventory](docs/evidence/user-equipment-inventory/README.md) reports no external RF equipment; [measured recommendations](docs/research/measured-recommendations.md) explicitly defer the common-path sensitivity comparison and report no ranking; [independent review](docs/evidence/rtl-dipole-independent-review/README.md) accepts this original absent-equipment branch.*

#### Scenario: Evaluation result is inspected
- **WHEN** a cross-receiver sensitivity ranking is reported
- **THEN** converter/reference settings, losses and uncertainties accompany the ranking
