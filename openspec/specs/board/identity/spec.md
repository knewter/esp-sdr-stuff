## Purpose

Keep the physical receiver identity and current firmware observation available for repeatable evaluations.

## Requirements

### Requirement: Observed ESP32 identity is preserved
The project SHALL retain the chip, flash and clock evidence identifying the attached original ESP32.

*Grounding: `docs/evidence/board-identification/README.md` and `docs/evidence/board-identification/chip-and-flash.log` record the direct ROM query.*

#### Scenario: Reader inspects the board record
- **WHEN** a reader opens the recorded chip query
- **THEN** they observe ESP32-D0WD-V3 revision 3.1, 40 MHz crystal and 4 MB flash

### Requirement: Current firmware is described from its boot
The project SHALL describe the observed firmware without assuming the expected runtime is installed.

*Grounding: `docs/evidence/board-identification/boot.log` records hello_world at 160 MHz and GPIO toggling.*

#### Scenario: Reader checks runtime identity
- **WHEN** a reader examines the recorded fresh boot
- **THEN** the observed GPIO-test application is distinguished from unconfirmed AtomVM
