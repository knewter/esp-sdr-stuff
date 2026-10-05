# Prospective clock safety case

From `5c5ddfcb`; no admission or physical gate changes.
The [observer protocol](forgix-clock-observer-protocol.md) remains authoritative.
[Reviewed artifacts](../evidence/forgix-clock-root-build-003/README.md) support
software task 3.2, not electrical qualification.

The guard requires six independently justified literal-true fields:

| Exact field | Decision still needed |
| --- | --- |
| `fpga_identity_assumptions_reviewed` | Matching assembly; grade/oscillator envelope |
| `pin_mapping_reviewed` | Actual B4/Y2 and G3/F3/F2 mapping |
| `electrical_safety_reviewed` | Compatible rails/banks; contention, pad/alias envelope |
| `reset_pin_ownership_reviewed` | Factory/watchdog/stopped-clock F2 ownership |
| `whole_loading_recovery_reviewed` | Fresh preservation, exact tuple, known closure/recovery |
| `startup_uid_reviewed` | Original UID; selected startup/reset limits |

Nominal 32 MHz may support a bounded diagnostic assumption grounded in primary
design; it cannot justify unsafe pins or voltage. Compilation measures neither
clock nor rails. MCU restoration does not restore unknown volatile FPGA state.

Root transfer needs UID/two 2 MiB originals, FPGA001/ARM003/all exports, whole/runtime
peer receipts, current 88-input/tool/archive/Nix proof and six evidence rows.
Private rows bind claim/status, evidence path+hash/class, assumptions, unresolved
items and reviewer. Independent review must bind the exact safety/registry tuple.
[Preparation](../evidence/forgix-clock-safety-case-preparation/README.md) pins the
full checklist; schema checks grant no access.

Separate transitions: safety→observer; observed counts plus physical envelope→
register qualification; measured SPI→60 s synthetic CRC/rate/pause/backlog trials;
verified spare pins/link→ESP transport. Observer 16 samples can abort 1024 periods;
nominal PIO 150 MHz is not calibration.

Survey018 at 2026-10-05T02:43:02.836597Z found no Forgix. Reconnect preserved data-USB.
Resolve assembly/electrical/reset evidence before loading. Internal observer/
register/synthetic needs no ESP wires. Hardware tasks stay open.
