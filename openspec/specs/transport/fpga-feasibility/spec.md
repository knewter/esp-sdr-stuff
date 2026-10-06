# FPGA feasibility Specification

## Purpose

A measured go/no-go decision for a useful FPGA transport or processing role, not a predetermined continuous SDR.

## Requirements

### Requirement: FPGA feasibility begins with actual hardware

The evaluation SHALL inventory the available FPGA and its electrical and host interfaces before selecting a capture transport.

*Grounding: [FPGA route decision inventory](docs/evidence/fpga-feasibility-decision/README.md) records the Forgix board, MCU, T8F49 speed grade 2, measured 32 MHz FPGA clock ([clock](docs/evidence/forgix-clock-episode-001/README.md), [register](docs/evidence/forgix-register-episode-001/README.md)), USB full-speed link, RP-side PSRAM, functionally verified SPIBone wiring and documented 3.3 V I/O; voltages are documentary, not metered.*

#### Scenario: Evaluation result is inspected
- **WHEN** the transport architecture is selected
- **THEN** the board model, I/O compatibility, clocking and payload budget are documented

### Requirement: Transport claims have measured continuity

The report SHALL distinguish sustained payload, framing overhead, backlog and data loss and make an evidence-based route decision.

*Grounding: [synthetic transport episodes](docs/evidence/forgix-synthetic-episode-001/README.md) report frames, records, CRC/sequence validation, FPGA FIFO drops, RP queue backlog and reconciliation at three offered rates (lossless at 256 and 1,024 B/s; 153/7,680 FIFO drops at 2,048 B/s during host stalls), and the [route decision](docs/evidence/fpga-feasibility-decision/README.md) keeps the Forgix off the ESP sample path on that measured basis.*

#### Scenario: Evaluation result is inspected
- **WHEN** a faster or continuous path is claimed
- **THEN** sequence/CRC counters and a sustained measurement justify that exact claim

### Requirement: Synthetic finalization retains failed outcomes

The synthetic coordinator SHALL keep lifecycle completion provisional through lease release, terminal persistence and output under the original 600-second acceptance clock. It SHALL durably establish the existing shared pending-finalization blocker before releasing its active lease and SHALL NOT qualify a failed, late or cancelled finalization from an older completed-looking receipt when corrective storage fails. All Forgix admission and access routes SHALL refuse a present or uncertain shared blocker while keeping owned resource closure available.

*Grounding: physical synthetic episodes 002 and 003 finished normally (CLI exit 0, original flash/factory verified, owned blocker closed) and passed independent result review; failed episodes 001 and 004 remained failed ([synthetic episodes](docs/evidence/forgix-synthetic-episode-001/README.md)). Release and corrective-storage failures are proven by the retained counterexamples and the offline synthetic lifecycle tests only, not by a physical fault.*

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

*Grounding: clock episode 005 finished normally (CLI exit 0, original flash/factory verified, owned markers cleared) and passed independent result review; failed episodes 001–004 left the shared pending blocker, which refused later Forgix access and recovery until resolved ([clock episodes](docs/evidence/forgix-clock-episode-001/README.md)). Uncertain-closure and terminal-storage quarantine of the held operator FD are proven by the offline clock tests only, not by a physical fault.*

#### Scenario: Shared refusal cannot be persisted
- **WHEN** closure is uncertain or terminal marker cleanup fails and both marker creation and exact owned-lease fallback fail
- **THEN** the exact held operator lock remains quarantined and no later shared operator or recovery is admitted automatically

#### Scenario: Clock terminal effects finish
- **WHEN** original-flash/factory verification, owned closure and required output/storage/cancellation/deadline effects pass
- **THEN** only exact owned markers may be cleared, the original FD remains held until final kernel teardown, and physical acceptance still requires independent session proof joined with actual CLI0, original deadline, owned-group/FD absence, marker absence and flock reacquisition
