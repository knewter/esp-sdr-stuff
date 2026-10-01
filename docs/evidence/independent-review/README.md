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
