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

### Requirement: Clock finalization preserves shared refusal

The clock coordinator SHALL keep completion provisional through required terminal
effects under its original clock. It SHALL retain exact owner-bound shared refusal
or its already-held operator FD when uncertain closure or terminal storage failure
prevents a trustworthy handoff. A failed correction SHALL NOT qualify older saved
normal facts. Cancellation SHALL remain latched through the last required effect;
uncertain FD closure SHALL NOT permit acting on a potentially reused descriptor.
The final original operator FD SHALL remain held through fallible terminal
effects and be released by final kernel process teardown; independent actual
process-exit and ownership evidence SHALL complete the staged release proof.

<!-- UNVERIFIED: Independent physical session/recovery proof remains pending. The original b37bd398 temporary-file/flock counterexamples are retained; corrected software, actual host exit/ownership controls, fresh runtime and current documentary candidate now pass the review recorded in docs/evidence/forgix-clock-current-documentary-review/README.md. This supplies no registry entry or physical admission. -->

#### Scenario: Shared refusal cannot be persisted
- **WHEN** closure is uncertain or terminal marker cleanup fails and both marker creation and exact owned-lease fallback fail
- **THEN** the exact held operator lock remains quarantined and no later shared operator or recovery is admitted automatically

#### Scenario: Clock terminal effects finish
- **WHEN** original-flash/factory verification, owned closure and required output/storage/cancellation/deadline effects pass
- **THEN** only exact owned markers may be cleared, the original FD remains held until final kernel teardown, and physical acceptance still requires independent session proof joined with actual CLI0, original deadline, owned-group/FD absence, marker absence and flock reacquisition
