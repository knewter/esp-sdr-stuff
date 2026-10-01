# Requirement-by-requirement checkpoint

Root revision reviewed: `367ed333014f7f54b1ba110c1c4017a33d20f427`,
October 1, 2026. This supplements the dated [review history](README.md),
[snapshot receipt](snapshot-verification.json),
[spectrum receipt](spectrum-verification.json),
[BLE receipt](ble-verification.json) and
[10-bit BLE receipt](ble-controls-verification.json).
No hardware handle was opened by this reviewer. The overall goal is incomplete.
The table applies the current requirements; it does not reduce them to the
subset that happened to succeed.

| Proposal requirement | Inspected support | Decision and remaining gate |
| --- | --- | --- |
| Firmware preservation is complete | Two independent private 4 MiB reads; matching hash, security and partitions; ignored mode-0600 backups; guarded provenance/offset regressions | Verified before experimental installation. |
| Restoration has physical proof | First and final full restoration readbacks match the original hash; fresh original application reset boots | Byte restoration and reset boot verified. Actual power removal/reapplication and matching boot remain open; recovery tasks 2.1/2.2 remain unchecked. |
| Snapshot integrity is measured | 600 physical payloads across six requested rate/format conditions independently match hash, CRC and sample count; timing/coverage independently reproduced | Accepted within the recorded snapshot transport scope; proposal archived after peer acceptance. No calibrated sample-rate or PLL claim. |
| Display provenance is visible | Actual 60.005-second 512-bin browser run; 7,205 CRC/sequence-verified frames and reconciled firmware totals; screenshots distinguish nominal, uncalibrated and gapped sampling | Accepted for this exact profile. Failed 1,024-bin run retained; no blanket reliability claim. |
| Reception claims use controlled signals | Independently chosen BLE manufacturer AD physically received in four 8-bit and one 10-bit snapshots; source schedules and exact settings retained | Narrow known-marker reception supported. Required three repeated on/off frequency-response pairs, usable-band characterization and each proposed extended-tuning reference remain open. |
| Measurement uncertainty is explicit | Filter/gain trial labels requested tuning/filter/gain, endpoints, uncontrolled background, nominal timing and absent RF calibration | Limitations correctly disclosed. Required measurement tasks remain open; a working packet at gain48/filter20 is not a calibrated gain/filter response. |
| Event detection has ground truth | Capture timestamps and source on/off control-plane schedule exist; exact RF event denominator is null | Open: at least 100 counted emissions, hits/misses/truncations and uncertainty against actual ground truth are unavailable. Wrong-channel historical monitor attempts and corrected EPERM attempt supply no count. |
| Decoding claims include payload verification | Pinned bounded blind decoder; private full waveforms replayed; independent whitening/CRC fixture and measured bit reconstruction; exact known AD and complete nominal packet windows | Known-payload decoder task accepted for the five distinct physical observations. Actual PDU type0, unprotected preamble errors and alternate slicer hypotheses are reported. This does not complete the event-ground-truth requirement. |
| FPGA feasibility begins with actual hardware | Forgix primary sources, PCI host enumeration, original-chip source and reproduced throughput/buffer calculations | Partial. Actual Forgix revision/clock/electrical interfaces and PCI-card identity/interface remain unverified. Manufacturer/math budgets cannot complete inventory task1.1. |
| Transport claims have measured continuity | Original-chip routes and synthetic benchmark gates documented; no FPGA programmed by the team | Open: sustained sequence/CRC transport, stall/backlog/timing measurements and conditional RF integration. USB wire-capacity rejection alone does not discharge those tasks. |
| Receiver recommendations state coverage and continuity | Four 65-second RTL internal-pattern tests, measured ESP gaps, direct-band limits and application matrix; no-FEC RDS independently reviewed in its separate receipt | Recommendations supported within stated evidence. Appropriate-antenna inventory/application gate remains open in the current plan; internal pattern checks are not RF loss proofs. |
| Same-signal comparisons identify conversion hardware | Disjoint direct tuning bands and absent same-signal sensitivity ranking explicitly documented | Open: physical converter/reference/antenna inventory and any required deferred comparison decision. No fabricated sensitivity ranking. |

The identity specs remain consistent with ESP32-D0WD-V3 rev3.1/4MiB behind
CP2102, the observed original GPIO application, and RTL-SDR BlogV4/R828D.
AtomVM is explicitly deferred by the user and excluded from this active audit.

The final restoration readback was independently rehashed at this checkpoint:
4,194,304 bytes, mode0600, SHA-256
`6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`.
Its public manifest explicitly records `power_cycle_proven: false`. This is
correctly separated from successful reset-boot and flash-byte restoration.

No checked task in the inspected current plans silently substitutes software
tests, a screenshot, a requested controller setting, a source schedule or
capacity mathematics for its required physical result. Only the snapshot
proposal is archived. Remaining proposals must retain their physical gates;
the presence of useful partial results does not authorize overall completion.
