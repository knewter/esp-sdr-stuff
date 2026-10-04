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
predeclared positive-offset band. Large excursions occur in OFF phases too. The separately declared
[advertising-mode counter pair](docs/research/ble-mode-counter-protocol.md)
diagnoses controller reporting only; implementation review and actual receipts
are recorded below. Neither result changes any original task criterion.

The [single physical mode pair](docs/evidence/ble-mode-counter-001/README.md)
has now completed with ten accepted commands, exact source/monitor agreement,
bounded duration and complete cleanup. Both modes report `0x3c/count0` and
their strict count gates remain failed. Original RF tasks remain unchecked.

The prospective [matched ten-bit gain controls](docs/research/ble-matched-gain-protocol.md)
hold receiver precision and bandwidth fixed while changing requested gain mode.
They require independent preflight and result review, complete restoration and
the original three-response criterion. No original task is closed by planning
or host tests.

Actual [matched controls](docs/evidence/ble-matched-gain-001/README.md) and
[independent review](docs/evidence/ble-matched-gain-independent-review/README.md)
now verify all 1,994 snapshots, source cleanup and both full restorations.
One fresh complete owned manual48 packet is partial reception proof. Hardware
has no owned packet; neither condition supplies three reciprocal source
responses, calibrated gain or emitted counts. Original task checks stay open.

A separately declared [single 100-event controller-count test](docs/research/ble-count-limit-100-protocol.md)
addresses the five-second/255-event timing mismatch while retaining all old
failures and the original 255-event reports. It requires a frozen private caller,
independent review, actual source/monitor count agreement and complete cleanup.
It supplies no SDR data or closure of an original task above.

That [actual legacy100 trial](docs/evidence/ble-count-limit-100-001/README.md)
retains `0x3c/count0`; [independent review](docs/evidence/ble-count-limit-100-independent-review/README.md)
accepts failure recording and cleanup. The separately prospective
[extended100 diagnostic](docs/research/ble-extended-count-limit-100-protocol.md)
tests the remaining mode/count combination with all original criteria intact.

The [actual extended100 result](docs/evidence/ble-extended-count-limit-100-001/README.md)
reports `0x43/count100`, but its monitor deadline makes the complete episode
failed. [Independent actual review](docs/evidence/ble-extended-count-limit-100-independent-review/actual-001-review.md)
verifies truthful failure retention and cleanup. No original task above closes.

## Fresh original eight-bit control

The [October 4 control](docs/evidence/ble-bluez-control-003/README.md) completes
three source ON/OFF pairs,1,260 independently verified snapshots, normal monitor
cleanup and full original4MiBrestoration. Entire decoder replay retains zero
CRC-valid packets; fixed prospective-band scalar replay supplies no reciprocal
source attribution. Sparse windows and unknown air emissions make this a null
control, not a detection-failure or missed-event rate. Original TrialB remains
gated. The next separate bridge-profile ladder starts ten-bit/BW20/manual48
and isolates precision, gain and bandwidth; earlier results remain unchanged.
No original task checkbox or accepted requirement changes.


## Ten-bit ladder control and fuller metadata

The [independently reviewed ten-bit/BW20/manual48 control](docs/evidence/ble-bluez-control-004/README.md)
verifies all 1,010 snapshots and full original restoration. Whole decoder replay
finds zero owned packets and three redacted CRC-valid packets from other sources;
these do not establish owned-source reception. Fixed-band scalar controls show
no repeated source-attributed rise. The next ladder condition is
8-bit/BW20/manual48, followed by 8-bit/BW20/hardware. Source ground truth and
original Trial B gates remain unmet; no physical checkbox changes.

The [fuller HCI parser](docs/evidence/ble-hci-metadata-preparation/README.md)
passes 134 focused checks and 23 independent probe groups. It retains additional
redacted requested fields for future profile validation. Earlier trial records
remain bound to their older helper; no omitted field, emitted PHY/power, air
count or reception is inferred from this software preparation.


The [next eight-bit/manual control](docs/evidence/ble-bluez-control-005-failed/README.md)
failed a short UART payload during its third source phase. All 1,047 saved
complete payloads and original restoration pass independent audit; the failed
fragment was not saved. Interrupted monitoring and a truncated source phase
prevent complete schedule/scalar qualification. Preserve this failed condition;
zero saved-row integrity failures does not describe the failed read. No task
or accepted requirement changes.


The [BW20/hardware condition](docs/evidence/ble-bluez-control-006/README.md)
completes all source pairs, 1,257 intact snapshots and original restoration.
Independent full decoder/scalar replay retains zero CRC-valid packets and no
repeated source-attributed nominal-band rise. HCI completions lie within the
predeclared guards; DBus acknowledgements alone are not synchronous completion.
The original BW12 condition is next after reviewed prefix retention. Original
Trial B and count/detection gates remain open; no checkbox changes.
