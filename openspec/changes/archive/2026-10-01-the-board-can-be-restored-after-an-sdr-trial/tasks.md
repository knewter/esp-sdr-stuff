## 1. Preserve the baseline

- [x] 1.1 Confirm the CP2102 identity and exclusive port ownership; record a fresh boot.
- [x] 1.2 Read the entire flash to ignored backups/original.bin; verify 4,194,304 bytes and record sha256sum output only.
- [x] 1.3 Read partition/security state and write a recovery checklist; verify every offset against the physical 4 MiB size.

## 2. Prove recovery

- [x] 2.1 After a separately scheduled SDR trial, restore the preserved image and power-cycle; capture a matching application boot.
- [x] 2.2 Review the restore evidence and record recoverable/not-recoverable with any failed step.

## Proof procedure

Backup: `esptool --port SELECTED_PORT read-flash 0 0x400000 backups/original.bin`; hash: `sha256sum backups/original.bin`. Restoration writes flash and belongs to the trial procedure; verify the saved manifest before choosing its write command.

Required outcome: A 4,194,304-byte backup with SHA-256 plus a recorded restoration boot; a backup alone does not close recovery proof.

## Recorded progress

[Physical preservation evidence](docs/evidence/firmware-preservation/README.md) verifies independent full reads and the recovery checklist.
[First restoration](docs/evidence/first-restoration/README.md) verifies the complete restored bytes and a matching reset boot.
[User-confirmed power cycling and matching subsequent application boot](docs/evidence/user-power-cycle-recovery/README.md) complete task 2.1. [Independent review](docs/evidence/power-cycle-recovery-review/README.md) completes task 2.2 with a recoverable decision. Physical power cycling is user-reported; UART opening may cause a further reset and the log is not a synchronized electrical cold-start measurement.
