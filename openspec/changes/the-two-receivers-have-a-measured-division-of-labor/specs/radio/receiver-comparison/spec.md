## Purpose

A receiver-by-application decision matrix grounded in this host and these two units.

## ADDED Requirements

### Requirement: Receiver recommendations state coverage and continuity

The report SHALL distinguish V4 direct HF-to-UHF coverage from ESP32 2.4 GHz snapshots with measured continuity limits.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** a reader chooses a receiver for an application
- **THEN** its tuning limits, gap behavior and evidence status are visible

### Requirement: Same-signal comparisons identify conversion hardware

The evaluation SHALL require a documented common signal path before comparing RF sensitivity across disjoint receiver bands.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** a cross-receiver sensitivity ranking is reported
- **THEN** converter/reference settings, losses and uncertainties accompany the ranking
