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

### Requirement: Synthetic finalization retains failed outcomes

The synthetic coordinator SHALL keep lifecycle completion provisional through lease release, terminal persistence and output under the original 600-second acceptance clock. It SHALL durably establish the existing shared pending-finalization blocker before releasing its active lease and SHALL NOT qualify a failed, late or cancelled finalization from an older completed-looking receipt when corrective storage fails. All Forgix admission and access routes SHALL refuse a present or uncertain shared blocker while keeping owned resource closure available.

<!-- UNVERIFIED: Prospective correction; two temporary-file counterexamples reproduced at 2ab2e7e, with no physical execution or false CLI0. -->

#### Scenario: Release and corrective persistence fail
- **WHEN** synthetic lease release returns late or its post-unlink directory sync fails, followed by corrective receipt storage failure
- **THEN** the episode remains failed, the durable shared pending blocker continues to refuse later operators, and the older saved lifecycle result does not qualify the episode

#### Scenario: Finalization finishes normally
- **WHEN** complete original-flash/factory verification and owned closure precede successful lease release, terminal persistence and output within the same clock
- **THEN** only the matching owned blocker may be closed, and actual CLI success, saved proof and blocker absence still require independent physical-result review
