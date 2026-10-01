## Purpose

A reproducible raw-I/Q and browser-spectrum baseline on the actual LX6 board.

## ADDED Requirements

### Requirement: Snapshot integrity is measured

The receiver evaluation SHALL count successful and failed CRC-checked snapshots for each advertised sample rate.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** the baseline capture series finishes
- **THEN** sample counts, error counts, transport rate and capture gaps are retained

### Requirement: Display provenance is visible

The evaluation SHALL associate a spectrum screenshot with its receiver, firmware, RF settings and capture gaps.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** a spectrum image is published
- **THEN** the record distinguishes measured RF from a design illustration
