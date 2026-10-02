# Independent dipole FM/RDS and receiver-comparison review

**Pass for the selected 101.1 MHz application and all five original
receiver-comparison tasks.** The original conditional inventory task is met
by documenting absent conversion/reference hardware and deferring the
same-signal sensitivity comparison. No cross-receiver sensitivity ranking or
new hardware capability is accepted by this review.

This reviewer opened no receiver, serial port or Bluetooth device. It replayed
the closed private MPX input and checked the public receipts, source code,
plot and comparison criteria offline. The reviewed fresh trial is
`83f050c6f109b5606c1908859bd39521fec45372`; the user inventory is
`d65882c828d05dd9a2b8afe97077eb94707ec9f5`.

## Fresh reception replay

The existing private input is 10,031,104 bytes, mode 0600, SHA-256
`57abd62b961d95ee8c0e4b471101e6962a3aa1b1b6dbc5768ba12f0e4f255e47`.
The pinned redsea binary and loaded liquid-dsp library match the published
hashes and clean source revisions. The reviewer ran MPX at 171,000 samples/s
with `--no-fec --show-raw --rbds --bler --time-from-start`; exit was 0 with
empty stderr. Output reproduced [the actual published NDJSON](../rtl-dipole-rds/live-decoder.ndjson)
byte for byte, SHA-256
`2b5b82ba24b83802b76a9072dcd93976326f6b46622ac46e48673da4e947ed07`.

An independent raw-block recount finds 317 emitted groups, 233 complete
groups, 1,137 accepted blocks, 131 missing blocks and 287 directly accepted
block-A values `0x9250`. These direct values avoid inherited JSON PI fields.
Independent base-26 arithmetic gives WXJC. The [station-owned site](https://www.wxjcradio.com/),
rechecked on 2026-10-02 UTC, identifies WXJC / Truth 101.1, consistent with
the requested frequency and decoded callsign. This is known-broadcast
attribution, without authenticated transmitter identity.

The pinned option parser disables correction; the block synchronizer accepts
the expected ten-bit syndrome/offset before publishing a valid block. The
published words omit check bits, so this review verifies the decoder's
checkword policy and reproducibility rather than a separate external CRC
recalculation. Counts cover emitted groups only, not unsynchronized groups
or an overall RF success rate.

The [actual plot](../rtl-dipole-rds/rds-decoding.png) and its data agree: 316
timestamped groups contribute 1,135 valid blocks and 286 direct PI blocks.
One final untimestamped partial group contributes two blocks and one PI to
the overall totals but is excluded from the plot. The chart labels antenna
model and RF amplitude limits explicitly; it is a decoder-result plot.

## Original acceptance gates

| Original gate | Reviewed evidence and decision |
| --- | --- |
| 1.1: at least 60 seconds at four specified V4 rates, complete output/loss/cleanup | All four [transport logs](../rtl-continuity/README.md) independently recounted: at least 65 seconds each, exit 0, cancellation and cleanup. The 2.048 MS/s trial reports one gap of at least 80 bytes; the other three report no gaps. Pass with modulo-256 test-pattern limitations retained. |
| 1.2: appropriate antenna and known source for one selected V4 application, settings and spectrogram or decoder result | User reports the current dipole; a new capture under that setup reproduces WXJC FM/RDS with [settings, source attribution and actual decoder plot](../rtl-dipole-rds/README.md). Functional suitability is demonstrated for this selected application. Pass. |
| 2.1: join V4 continuity and ESP acquisition/transfer timing in an application matrix, distinguish measurements/claims | [The measured matrix](../../research/measured-recommendations.md) separates internal V4 transport and manufacturer coverage from ESP nominal windows and measured delivery gaps. All 600 snapshot CSV count/CRC flags, grouped medians and nominal coverage arithmetic were rechecked; prior [independent waveform/transport review](../independent-review/README.md) remains the underlying proof. Pass. |
| 2.2: inventory conversion/reference hardware; if absent defer same-signal comparison | [User inventory](../user-equipment-inventory/README.md) reports no separate RF equipment. No common converter/reference path exists in the reported inventory; sensitivity comparison is explicitly deferred under the original conditional task. Pass as documented deferral, not as a performed RF comparison. |
| 2.3: recommendations for continuous narrowband reception, 2.4 GHz observation and optional FPGA research | The measured recommendations state V4 stream/test limits, ESP snapshot gaps/verified owned packets, and prospective FPGA constraints without claiming local FPGA bring-up. Pass. |
| Requirement: tuning limits, continuity and evidence status are visible | V4 manufacturer HF-to-UHF coverage is labeled as such; ESP modem commands are not equated with verified usable tuning range. Snapshot gaps, nominal clock assumptions and unverified applications are visible in the matrix and linked proof. Satisfied. |
| Requirement: sensitivity rankings identify a documented common signal path | No cross-band sensitivity ranking is reported. Missing conversion/reference hardware and calibration keep that comparison deferred. Satisfied without pretending such a path was measured. |

## Limits and completion scope

The current dipole's model, arm lengths, orientation and physical attachment
were not independently inspected. The fresh successful selected application
establishes functional suitability here; neither the original task nor this
verdict requires or implies all-band antenna characterization. No earlier
antenna identity is inferred, and no antenna-change improvement is claimed.
The 30.162-second process produces 29.331 seconds of nominal MPX samples;
this is not calibrated RF clock or continuity proof.

The manufacturer [V4 design description](https://www.rtl-sdr.com/rtl-sdr-blog-v4-dongle-initial-release/)
supports the sourced HF-to-UHF coverage description, not an independently
measured sweep. The ESP remains a gapped 2.4 GHz snapshot experiment, and the
owned FPGAs remain unproven locally. Antenna gain, sensitivity, range, every
tuning point, source-event denominator and FPGA hardware gates remain outside
this comparison's completed scope.

[Numerical checks](numerical-checks.json) record exact source/binary/input/output
hashes, independently counted results, four transport trials and six ESP
timing groups. Historical planning and recommendations still contain earlier
inventory-open wording at the reviewed checkpoint; the completing author
must reconcile that prose with the new evidence while retaining these limits.
