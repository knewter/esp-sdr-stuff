## 1. Define controlled inputs

- [x] 1.1 Inventory the source/reference/attenuator equipment; write settings and known limits before collecting RF data. Proof: [user equipment inventory and prospective settings/limits](docs/evidence/user-equipment-inventory/README.md). No external reference/attenuator is reported; the host BLE source remains uncalibrated and uncounted. This closes inventory only, not later RF response gates.
- [ ] 1.2 Record at least three repeated source-on/source-off pairs at known 2.4 GHz channels; compare tone/channel location and background.

## 2. Measure receiver limits

- [ ] 2.1 Sweep advertised filters and gain on a fixed input; record spectra, center offset and clipping indicators.
- [ ] 2.2 Test each proposed extended-tuning point against a known reference signal; reject alias-only or unconfirmed points.
- [ ] 2.3 Publish plots, source settings and uncertainties, and decide the band/window settings usable for later experiments.

## Proof procedure

Physical procedure: fixed source, fixed antenna placement, paired on/off captures, three repeats per condition. The capture and analysis tools consume saved manifests and CSV. Acceptance requires the known-source response and repeated observations.

Partial proof: [owned BLE decoding](docs/evidence/ble-owned-decoding/README.md), [filter/gain pilot](docs/evidence/rf-controls-trial/README.md), and [actual source controls](docs/evidence/ble-dumpcap-source/README.md). These trials do not yet close any complete task above; their settings and limitations must remain visible in later reports.

Required outcome: Three repeatable source-on/source-off pairs with known center frequencies; each claimed extra tuning point has an independently known signal and uncertainty.

## Declared supporting diagnostics

The [DC-first saved-data replay](docs/research/ble-dc-first-replay.md) and
[separate register-state observation](docs/research/receiver-register-observation-protocol.md)
support diagnosis of the fresh nulls. They preserve the task criteria above.
Source review, exact input/artifact integrity and independent result replay are
required; a register readback or saved-data decoder success is not substituted
for a controlled live RF response or a counted emitted event.

Completed supporting evidence: the [waveform audit](docs/evidence/ble-waveform-comparison/README.md)
reproduces the old outcomes; the [independently checked DC-first replay](docs/evidence/ble-dc-first-independent-review/README.md)
is null on fresh captures and regresses three historical results, so it remains
unadopted. Offline register firmware/host tests exercise actual C with synthetic
MMIO; build, installation lifecycle and hardware observation are not accepted
by those tests. No original task above is completed by these diagnostics.

The separately guarded [physical register observation](docs/evidence/receiver-register-observation-002/README.md)
now completes 20 valid captures/81 ordered stages with full original restoration.
All sampled forced-selector fields are 48 and bit23=1. Actual measured hook cycles
and the [retained failed first attempt](docs/evidence/receiver-register-observation-001/README.md)
remain explicit. This is readback evidence, not a controlled source response,
calibrated gain, emitted count or closure of any original task above.

The [guarded ON/OFF waveform audit](docs/evidence/ble-on-off-waveform-audit/README.md)
replays all 2,248 fresh snapshots and finds no repeated increase in the nominal
target band. Large excursions occur in OFF phases too. The separately declared
[advertising-mode counter pair](docs/research/ble-mode-counter-protocol.md)
diagnoses controller reporting only; implementation review and actual receipts
are recorded below. Neither result changes any original task criterion.

The [single physical mode pair](docs/evidence/ble-mode-counter-001/README.md)
has now completed with ten accepted commands, exact source/monitor agreement,
bounded duration and complete cleanup. Both modes report `0x3c/count0` and
their strict count gates remain failed. Original RF tasks remain unchecked.
