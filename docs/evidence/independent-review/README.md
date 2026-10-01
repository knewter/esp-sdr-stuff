# Independent review checkpoint

Evidence class: **independent host inspection and software regression tests**.
Review date: October 1, 2026. Initial reviewed repository checkpoint:
`b2ff0b5ce72a98bf4e9ee38024f8cb9c0c55c9ab`.

This review is separate from the operator performing ESP32 trials and the
operator performing RTL-SDR trials. The reviewer never opened a device port,
configured an FPGA, or wrote device flash. This is a checkpoint, not a final
completion approval. Physical measurements arriving after this revision need
their own review.

## Preservation and installation gate

The reviewer independently read the private files without changing them.
Both full images are exactly **4,194,304 bytes**, their SHA-256 values match the
[public preservation manifest](../firmware-preservation/manifest.json), both
have filesystem mode `0600`, and Git's ignore rules exclude both images.
The partition parser independently applied to the saved original image
reproduces the manifest entries. The current partition table carries the
expected MD5 trailer; partitions fit the physical flash and do not overlap.

[Security output](../firmware-preservation/security.log) shows secure boot V1
and V2 disabled and encryption count zero. The recovery instructions preserve
the original header settings and explicitly require fresh boot evidence plus
actual power removal/reapplication. Backup verification passes the installation
prerequisite. It does **not** establish post-trial recovery.

The GitHub Actions API independently reports upstream run `36905645289` as
successful with head revision
`550fadea4d00a9e26ce921c5832167becb3dc20c`. The
[acquired artifact metadata](../firmware-artifact/manifest.json) selects the
original `esp32` target, not S3 or C5. Application image-info reports the correct
chip ID, valid application checksum/hash and an allowed revision range covering
this revision 3.1 board. Bootloader, table and application offsets are `0x1000`,
`0x8000` and `0x10000`; all fit 4 MiB. Artifact hash verification is integrity
against the upstream manifest, not a signature or an independent local build.

## Wire protocol and statistics review

The reviewer fetched the receiver, burst-serial and spectrum implementations
at the pinned upstream revision and compared the host parser against them.
Rate codes, CAP16/CAP20 sizes, signed I/Q unpacking, fragmented reads, CRC32,
SPC1 header fields and SPECEND field order match the reviewed implementation.
The existing **nine protocol tests pass**. Their synthetic bytes prove parser
behavior and do not constitute physical RF observations.

Two correctness issues were found and reported before final acceptance:

- Endpoint fraction used `abs(component) >= full_scale - 1`, which additionally
  counts the second-most-negative code. True signed endpoints are exactly
  `-full_scale` and `full_scale - 1`. This is still an endpoint statistic,
  not proof that ADC clipping occurred.
- The spectrum session originally checked increasing synthetic sample index
  but did not reconcile frame sequence and final firmware totals. A valid CRC
  alone cannot detect a completely missing frame or support zero-loss claims.

The firmware-tools author added corrections. The independent
[trial integrity regressions](../../../tests/test_spectrum_trial_integrity.py)
then passed against the author's corrected worktree: valid complete session,
CRC corruption, valid-CRC sequence gap, inconsistent end totals, early stop,
short firmware duration despite host delay, inflated processed sample count,
missing snapshot gap flag and nonzero firmware status. All cases require the
mock device handle to close. These tests should be integrated **after** the
corresponding fixes. They deliberately fail if the old permissive reader is
used.

The host's timestamps and upstream synthesized sample indices do not calibrate
the RF sample clock or independently identify exact capture-start time.
Nominal coverage must retain that limitation. Host rendering screenshots prove
the renderer operated; a screenshot alone does not establish RF reception.

## FPGA interpretation

The [FPGA checkpoint](../fpga-inventory/README.md) correctly distinguishes
read-only PCI enumeration, source specifications and mathematical budgets.
The reviewer reproduced the capacity equations: at 80 million complex pairs/s,
20-bit packed pairs demand **200 MB/s**. A 12 Mb/s USB wire has a **1.5 MB/s**
upper bound before overhead. A finite FIFO cannot cure this sustained mismatch.
The maximum 16,380-pair capture lasts 0.20475 ms at the nominal rate and contains
40,950 packed bytes. These are calculations, not measured throughput.

The documentation does not misinterpret the PCI BAR aperture as RAM or assume
the original LX6 exposes the S3's dedicated-GPIO streaming bus. The Forgix
schematic's RP-managed PSRAM is not a direct FPGA sample store. Actual board
revision/clock/voltage, recovery, transport benchmarks and RF integration remain
open; the direct USB capacity result cannot close those separate gates.

## Acceptance audit at this checkpoint

| Proposal | Evidence inspected | Acceptance state |
| --- | --- | --- |
| Board recovery | Two actual private full reads, public hashes/security/partitions, recovery instructions | Preservation verified; restoration and physical power-cycle boot open |
| Repeatable snapshots | Original-chip artifact, pinned source and host parser tests | No committed physical capture series or 60-second browser session at reviewed checkpoint |
| Controlled 2.4 GHz response | Planned source-on/off, filters/gain and reference criteria | Repeated controlled RF response, clipping/uncertainty and extended-point reference proof open |
| Short-burst applications | Planned counted events and independent payload verification | Source ground truth, counted hits/misses, complete waveform and verified decoder result open |
| FPGA feasibility | Read-only host survey, primary design review, reproduced capacity math | Capacity-limited direct USB route documented; actual electrical/transport/RF gates open |
| Receiver division of labor | V4 identity and planned continuity/application evidence | Local sample-loss tests, application result and joined measured recommendation await review |
| AtomVM | User exclusion and explicit deferred status | Outside active goal; keep deferred |

The final audit must inspect every named task and requirement against committed
physical evidence. Successful software tests, documentation or partial negative
feasibility results do not silently discharge unperformed hardware tasks.

## Validation scope and limitations

Running the copied Python suite without first generating a site yielded
**53 passing tests** and three expected site-output failures due to absent
generated `work.json` and `site/dist`. This is an unbuilt-worktree precondition,
not a website validation result. The required build, strict OpenSpec validation
and browser checks remain separate final checks. A targeted nine-test protocol
run passed, and the additional nine integrity regressions passed against the
corrected tools as described above.

A scan of committed evidence text found no unredacted MAC addresses or obvious
credential/network-name assignments. This is a targeted text scan, not a claim
that every possible secret encoding is impossible. Raw flash and raw RF files
remain excluded; published sample statistics do not require their contents.

Primary references: [pinned receiver implementation](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c),
[pinned spectrum implementation](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/common/spectrum.c),
[upstream artifact build](https://github.com/ESPARGOS/esp-sdr/actions/runs/36905645289),
[esptool commands](https://docs.espressif.com/projects/esptool/en/latest/esp32/esptool/basic-commands.html),
and [official Forgix specifications](https://forgix.tech/).

## Follow-up: corrected protocol tools and measured RTL evidence

Reviewed root checkpoint `d5da757` incorporates the integrity fixes and the
independent regressions. Running the corrected committed tools passed **10
capture/protocol tests, nine independent session-integrity tests, and five RTL
tests**. The two previously reported software issues are resolved at this
checkpoint. These 24 targeted tests are distinct from the full site validation.

The reviewer independently reparsed all four
[RTL continuity logs](../rtl-continuity/README.md) and reconciled every parsed
field with their capture manifest. All four trials exceed 65 seconds before
SIGINT, have normal cleanup output and exit code zero. The 2.048 MS/s log reports
one discontinuity of at least 80 **bytes**, despite the integer final loss-per-
million result being zero. The other three logs report no discontinuities;
the modulo-256 checker does not prove absolute zero data loss. Task 1.1's
named 60-second four-rate transport test is supported.

The reviewer also independently read the private normal-IQ file used in the
[passive FM survey](../rtl-fm-survey/README.md). Its length is 10,240,000 bytes
and SHA-256 matches the public IQ manifest. Re-running the documented quadrature
demodulation/PSD computation reproduced all published numerical results,
including the **19,000 Hz** peak and **56.2560579782692 dB** ratio to the defined
nearby median. This is reproducible structure consistent with an FM multiplex,
not an independently identified station, verified antenna, calibrated RF SNR,
decoded audio/stereo/RDS result, or an RF-mode continuity measurement. Comparison
task 1.2 appropriately remains open.

The [BLE source registration record](../ble-source-registration/README.md)
correctly documents accepted configuration and successful unregistration as
commanded advertising episodes. Autonomous controller repetition means those
episodes cannot supply exact over-the-air emission counts. They can form
controlled on/off interventions if actual receiver response is separately
measured, but do not satisfy the short-burst counted-emission/payload criteria
on their own.

## Follow-up: restoration, transport diagnostics and flash safeguards

Reviewed root checkpoint `4ac9017`. The reviewer independently reread the
private full-image restoration readback without opening a hardware handle:
**4,194,304 bytes**, with SHA-256 equal to both the public restoration record
and preserved original. The [first restoration](../first-restoration/README.md)
also contains the original `hello_world` / ESP-IDF v5.4-dirty / 160 MHz boot and
pin-toggle behavior. Full byte restoration and reset boot are supported.
Actual power removal/reapplication remains unrecorded; its acceptance gate
stays open.

The upstream 2 Mbaud image and configuration-only 1 Mbaud image both entered
`app_main`, but no protocol replies were received. These observations do not
establish an ADC failure, unsupported silicon, initialization stall or a
measured physical UART rate. A requested 2 Mbaud host setting was reported as
1 Mbaud by the kernel, which is relevant transport evidence, not a waveform
measurement of the UART pins.

The [115200 startup diagnostic](../sdr-diagnostic-trial/README.md) subsequently
reached its command-loop-ready marker and answered INFO, SYNC, BAUD?, CAPS and
LIMITS?. This proves functioning initialization and command transport **for
the instrumented diagnostic build**. No IQ/RF acceptance follows from those
replies. Diagnostic prints also occur inside subsequent radio reconfiguration,
so this image cannot be treated as a clean protocol/RF baseline. A clean
configuration-only transport variant must be evaluated separately.

The reviewer inspected the diagnostic source patch and recomputed its exact
SHA-256:
`fb2d465c97f8385b199b51cc8878ed5988790584f22c758c62a0a26dfee7698c`.
It adds ROM UART markers around existing initialization operations, preserving
the source base `550fadea` and pinned SDK `25fe69f9`. Added instrumentation
changes timing; successful diagnostics do not prove the original build's
timing was identical.

The first flash-guard review identified two generic input-validation gaps:
an alternate manifest claiming the full original source revision could skip
variant provenance checks, and canonical offsets alone did not prevent a
part from overlapping the next partition. Both were corrected in `4ac9017`:
original acquisition metadata must match the canonical recorded manifest;
all three part names/offsets are fixed; positive sizes must fit their respective
bootloader/table/factory bounds.

The independent [flash-guard regression suite](../../../tests/test_flash_trial.py)
passes **23 tests** against that corrected implementation. It covers pinned
upstream acquisition, accepted SDK/source and config-only baud variants,
the exact diagnostic patch and its restricted baud, incorrect provenance,
unexpected configuration/source changes, part integrity/names/offsets and
partition overlap, private-baseline completeness/hash/read verification,
secure-boot/encryption checks, occupied or ambiguous port rejection, complete
restoration without header overrides, failed-write records and public-log
redaction. Every subprocess call is mocked: these tests neither open a port
nor perform a flash operation. Fake fixture binaries exercise the guards,
not esptool's actual image parser or physical flash integrity.

The guard trusts the reviewed committed preservation/security/build records;
it is not an authenticity proof against arbitrary alteration of those trusted
records. The stable path was physically identified before operations, and
esptool checks ESP32 silicon. The flash wrapper restricts the selected path
but does not independently query the USB VID/PID on every invocation.

## Peer acceptance: physical snapshot and browser baseline

The raw-snapshot review covers root checkpoint `a76167c`; firmware/build
provenance covers `205ba74` and physical installation `f934b7e`. The
[independent numerical receipt](snapshot-verification.json) records the
recomputed results. The reviewer read **all 600 private payload files**,
totalling **22,113,000 bytes**, without opening the receiver. Every SHA-256,
CRC32 and payload length matched its public CSV row; every requested and
returned count was 16,380 complex pairs. Each of the six format/rate groups
has exactly 100 distinct attempts. Host command/header/payload time deltas,
group durations, nominal coverage, medians and 95th percentiles reconcile
with the public results and plotted summary.

The reviewer separately read all three actual clean 921600-baud binary parts:
lengths/hashes match both the build manifest and physical installation manifest.
The actual source checkout is pinned to `550fadea` with no tracked changes;
the actual SDK checkout is pinned to `25fe69f9` with no tracked changes.
Boot and query records identify the configuration-only original-ESP32 image.
The updated retry/fence handshake passes its two startup regressions, giving
12 capture/protocol tests plus nine independent session-integrity tests.

The subsequent [512-bin browser session](../spectrum-baseline/README.md)
was independently checked against its private stream, public CSV/result
records and visually inspected completed-browser still. The
[independent spectrum receipt](spectrum-verification.json) records the audit:

- 3,928,960 private bytes reproduce the operator's stream SHA-256.
- All **7,205 spectrum frames** and **236 statistics frames** have valid CRC32.
- Spectrum sequences are contiguous from 0 through 7,204; sample indices
  increase, frame shape/sample totals match, and every spectrum marks gaps.
- Every public per-frame field and min/max/mean power aggregate matches the
  private bytes. Firmware totals reconcile to 7,205 FFTs and 3,688,960 pairs,
  zero final status and no user-stop flag.
- Firmware duration is **60.005197 s** and host duration **60.005218725 s**.
  Nominal sampled time is 0.046112 s, giving **0.076846649%** nominal coverage.
  The completed still displays the same settings, frame count and gap warning.

The final firmware end report is retained as public metadata rather than inside
the private binary file. The checked private frames substantiate its count/
pair totals; software/host timestamps still do not calibrate the sample clock.
The still labels uncalibrated power and nominal rates and makes no identified-
signal claim. The [earlier 1024-bin failure](../spectrum-baseline-1024-failed/README.md)
remains visible. A successful 512-bin trial does not erase that CRC failure
or establish reliability for every advertised FFT profile.

**Peer decision:** every named snapshot-proposal gate now has supporting
physical evidence. Commit the browser evidence and matching task/spec updates
before archiving this proposal. Its fulfilled installation dependency is the
verified full-flash preservation gate; physical power-cycle recovery remains
a separate open task. This acceptance covers raw-I/Q transport and bounded
display with documented gaps. It does not accept controlled-source RF response,
PLL lock, sensitivity, calibrated clocks, event-hit probability, payload
decoding, FPGA integration or completion of the overall goal.

The reviewer also checked the
[measured recommendations](../../research/measured-recommendations.md) at
`28d13a6`: they distinguish manufacturer coverage, measured USB continuity,
nominal ESP windows, unverified known-signal/antenna claims, disjoint direct
bands and unresolved FPGA electrical/transport gates. The recommendations
fit the measured scope; the remaining proposal tasks should stay open.
