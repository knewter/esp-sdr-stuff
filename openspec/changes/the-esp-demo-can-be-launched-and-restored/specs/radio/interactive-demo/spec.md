## Purpose

Let the operator repeat a bounded, observable ESP32 radio-spectrum demonstration with verified firmware, honest capture limits and independently checked restoration.

## ADDED Requirements

### Requirement: One Task command runs a verified physical spectrum demonstration

<!-- UNVERIFIED: The new orchestration requires fresh physical execution and independent review. -->

The system SHALL provide a documented Nix-backed Task command that identifies the connected ESP32, verifies its preserved current baseline and receiver artifacts before writing, launches a local spectrum viewer, and records a successful 60-second physical acquisition with valid frame CRCs, sequence and firmware end totals. It SHALL reject occupied devices, unexpected baseline contents and invalid artifacts before receiver installation.

#### Scenario: The preserved board completes the demo
- **WHEN** the operator runs the documented command with a verified receiver artifact and fresh private and public destinations
- **THEN** the viewer receives actual hardware spectra for at least 60 seconds, all received frame integrity and end-total checks pass, and a sanitized session receipt records the settings, artifact hashes and results

#### Scenario: Preflight fails
- **WHEN** device identity, exclusive ownership, baseline contents or artifact validation fails
- **THEN** the command reports failure without installing the receiver or overwriting an unexpected current image

### Requirement: The viewer and evidence disclose snapshot limitations

<!-- UNVERIFIED: The new viewer lifecycle and its fresh hardware evidence have not been reviewed. -->

The system SHALL label snapshot reception gaps, nominal sample rates and uncalibrated power units in the live viewer and saved evidence. It SHALL retain live and completed display evidence linked to the physical session, and retain failed trial records. Raw RF payloads, full flash images, device identifiers and unsanitized transcripts SHALL remain outside Git and the public site.

#### Scenario: A live display updates smoothly
- **WHEN** the viewer displays successive spectra
- **THEN** it identifies reception as separate snapshots with gaps and does not present display updates as continuous RF coverage or power as calibrated dBm

#### Scenario: Acquisition fails
- **WHEN** a frame integrity, duration or end-total check fails
- **THEN** the evidence reports a failed session and preserves available sanitized results without replacing the failure with a successful trial

### Requirement: Demo cleanup verifies the restored original firmware

<!-- UNVERIFIED: The new command's restoration and interruption paths need fresh physical and host-test proof. -->

The system SHALL close its owned capture processes and serial handles before attempting restoration after installation, including success, failure and cancellation. It SHALL restore the preserved original image, independently read and compare all 4,194,304 flash bytes, and observe a matching original-application boot before reporting verified recovery. It SHALL provide a documented standalone recovery Task command and report restoration failure explicitly. Software reset observations SHALL NOT be labeled as physical power cycling.

#### Scenario: Successful capture returns to the original application
- **WHEN** the bounded hardware acquisition completes
- **THEN** the original image is restored, full readback matches the preservation hash and the matching original application boot is recorded before the command exits successfully

#### Scenario: An installed receiver trial is interrupted
- **WHEN** the operator cancels the command or acquisition fails after receiver installation begins
- **THEN** cleanup first closes owned hardware operations, attempts verified restoration and retains both the trial failure and recovery outcome

#### Scenario: Recovery cannot be verified
- **WHEN** an owned hardware process cannot be closed, restoration fails, readback differs or the original boot is absent
- **THEN** the command exits with an explicit unverified recovery result and gives the standalone recovery procedure rather than claiming success
