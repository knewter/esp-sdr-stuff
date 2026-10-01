## Context

See [proposal](proposal.md) for the problem and scope. The hardware identity is recorded separately from untested reception and transport behavior.

## Goals / Non-Goals

**Goals:** A recovery route that restores the observed GPIO test, or a separately selected AtomVM image, with clearly distinct provenance.

**Non-Goals:** No flash dumps on the site; no assumption that the current image is AtomVM; no unrequested radio transmission.

## Decisions

Use full-chip preservation because the current boot image declares only 2 MB while the physical flash is 4 MB. Restore the original bytes rather than reconstructing unknown partition state. An AtomVM upgrade is a separate choice.

The host records revisions/settings/results; firmware owns modem and memory access; an FPGA, if selected, owns only its explicitly measured transport/processing boundary.

## Risks / Trade-offs

The dump may contain private data. Keep it ignored. A successful write/read verification does not prove the restored application boots.

## Validation and decision

A 4,194,304-byte backup with SHA-256 plus a recorded restoration boot; a backup alone does not close recovery proof.

Backup: `esptool --port SELECTED_PORT read-flash 0 0x400000 backups/original.bin`; hash: `sha256sum backups/original.bin`. Restoration writes flash and belongs to the trial procedure; verify the saved manifest before choosing its write command.

## Visual plan

[Experiment flow and provenance](docs/design/the-board-can-be-restored-after-an-sdr-trial/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.
