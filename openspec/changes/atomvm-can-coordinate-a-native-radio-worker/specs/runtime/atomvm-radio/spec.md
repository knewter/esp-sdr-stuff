## Purpose

A reasoned decision about AtomVM control of capture, not high-rate sample handling in Erlang.

## ADDED Requirements

### Requirement: Native capture has bounded ownership

The prototype SHALL reserve capture memory and use bounded control/results at the VM boundary.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** the VM initiates a capture
- **THEN** native code owns sample acquisition without exposing reused memory to an Erlang process

### Requirement: Runtime feasibility is measured

The evaluation SHALL record capture integrity, memory use and VM responsiveness before accepting single-chip integration.

<!-- UNVERIFIED: The proposed experiment has not run on the physical hardware. -->

#### Scenario: Evaluation result is inspected
- **WHEN** the coexistence trial completes
- **THEN** the decision cites the measured cycles and comparison baseline
