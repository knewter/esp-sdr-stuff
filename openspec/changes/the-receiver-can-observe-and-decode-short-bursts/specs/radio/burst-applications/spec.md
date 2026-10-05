## Purpose

Decide which interference, educational DSP and short-burst applications are useful on this board.

## ADDED Requirements

### Requirement: Event detection has ground truth

The evaluation SHALL report observed and missed controlled events against a recorded source count.

<!-- UNVERIFIED: Five owned packets decode, but no usable recorded source denominator exists. Three initial finite source-only HCI trials had no termination; subsequent timer diagnostics report an actual zero field, and a 262-snapshot RF discriminator is inconclusive. Requested limits and the unvalidated zero field do not establish emitted-event counts. Hit rates and unresolved misses/truncations remain unknown. See docs/evidence/ble-counted-source-smoke/README.md and docs/evidence/ble-zero-counter-rf/README.md. -->

#### Scenario: Evaluation result is inspected
- **WHEN** event detection is assessed
- **THEN** hit rate includes missed windows and truncated events

### Requirement: Decoding claims include payload verification

The report SHALL label decoding demonstrated only when a complete capture yields the independently known payload.

*Grounding: [actual protected-PDU CRC and exact known-marker verification](docs/evidence/ble-owned-decoding/README.md) records four complete captured packets, private input hashes, bounded blind decoder revision and payload comparison; [10-bit control example](docs/evidence/ble-controls-decoding/README.md) adds a fifth packet. Preamble/access hard-decision errors remain explicit and outside the protected CRC.*

#### Scenario: Evaluation result is inspected
- **WHEN** a decoding capability is reported
- **THEN** the waveform, decoder revision and payload comparison are available

### Requirement: Longer primary diagnostics retain separate qualification and opportunity units

The evaluation SHALL keep a separately timed zero-data primary diagnostic's
source qualification, acquisition-window coverage and observations distinct
from counted v1 controller events, independently emitted RF events and the
original acceptance gates.

<!-- UNVERIFIED: Timed-v2 source and built archive pass offline independent review in docs/evidence/ble-primary-timed-source-host-preparation/README.md; caller admission, physical source qualification and the new receiver/holder remain unverified. The completed fixed receiver001 has11 guarded ON windows and no CRC-valid primary; see docs/evidence/ble-primary-zero-data-receiver-001-review/README.md. Prospective fields, ownership, clocks and proof gates are in docs/research/ble-primary-timed-zero-data-v2-protocol.md. -->

#### Scenario: A timed source condition is admitted
- **WHEN** a longer timer-limited primary condition is proposed after the fixed diagnostic
- **THEN** its exact finite profile, observed timer status and complete cleanup receive independent source-only qualification before receiver action
- **AND** v1 source/image/guard and previous frozen private inputs remain unchanged

#### Scenario: Longer diagnostic coverage is reported
- **WHEN** the timed condition's saved source and receiver records are reviewed
- **THEN** the report counts whole guarded ON acquisition windows per repetition and retains every OFF, boundary, sparse and failed outcome
- **AND** a completed-count byte, requested duration or window threshold does not establish an air denominator, event rate, three reciprocal RF responses or original Trial B acceptance

#### Scenario: Verification cost requires new preparation
- **WHEN** source003 full verification refuses the existing timed-source admission budget
- **THEN** a separately reviewed source004 and outer gate SHALL retain every fresh local byte/import/reference/NAR/archive predicate and complete worker ownership within unchanged source45/caller30/native32/whole165/outer300 bounds
- **AND** hermetic pinned selection and exact locked public input retrieval occur only before monitor; no selector, fetch or build occurs inside45
- **AND** neither architecture review nor a parallel allocation estimate admits a source or closes any physical acceptance gate

<!-- UNVERIFIED: source004 is prospective only; actual source003 cost/refusal is retained in docs/evidence/ble-primary-timed-startup-preparation-review/README.md. The independently reviewed design prerequisite and private provenance pins are in this change's design.md. Actual current tuple, complete timing, source and receiver qualification remain pending. -->

#### Scenario: Complete verification exceeds the source budget
- **WHEN** a saved complete read-only preparation is too slow for timed admission
- **THEN** a separately identified bounded measurement evaluation SHALL retain every original fresh proof, ownership and deadline predicate and distinguish measured operation brackets from inferred costs
- **AND** complete current-tuple timing and independent review precede any separately planned optimization or source qualification
- **AND** a partial compatible proof, reduced input set, cached content result or clock extension cannot establish fit

<!-- UNVERIFIED: The accepted historical source004 read-only proof in docs/evidence/ble-primary-timed-source004-readonly-review/README.md is not source45 timing. Saved-ledger decomposition and the corrected003 cancellation-only baseline are pinned separately in design.md. Instrumentation, actual current-tuple costs and fit remain prospective; all physical tasks and original air/count/reception gates remain open. -->
