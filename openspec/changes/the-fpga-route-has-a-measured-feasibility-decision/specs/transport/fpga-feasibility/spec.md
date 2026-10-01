## Purpose

A measured go/no-go decision for a useful FPGA transport or processing role, not a predetermined continuous SDR.

## ADDED Requirements

### Requirement: FPGA feasibility begins with actual hardware

The evaluation SHALL inventory the available FPGA and its electrical and host interfaces before selecting a capture transport.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** the transport architecture is selected
- **THEN** the board model, I/O compatibility, clocking and payload budget are documented

### Requirement: Transport claims have measured continuity

The report SHALL distinguish sustained payload, framing overhead, backlog and data loss and make an evidence-based route decision.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** a faster or continuous path is claimed
- **THEN** sequence/CRC counters and a sustained measurement justify that exact claim
