## 1. Measure the existing receiver

- [x] 1.1 Run 60-second sample-loss tests at 1.024, 2.048, 2.4 and 2.56 MS/s while the device is idle; retain complete output and stop/cleanup results. Proof: [physical transport measurements](docs/evidence/rtl-continuity/README.md).
- [x] 1.2 Use an appropriate antenna and known source to verify one selected V4 application; publish receiver/source settings and a spectrogram or decoder result. Proof: [fresh current-dipole RDS](docs/evidence/rtl-dipole-rds/README.md) and [independent replay](docs/evidence/rtl-dipole-independent-review/README.md).

## 2. Compare useful capabilities

- [x] 2.1 Join the V4 continuity results and ESP acquisition/transfer timing into one application matrix; label local observations versus manufacturer/upstream claims. Proof: [measured application matrix](docs/research/measured-recommendations.md).
- [x] 2.2 Inventory conversion/reference hardware before any same-signal RF test; if absent mark that comparison deferred rather than fabricate a ranking. Proof: [user equipment inventory](docs/evidence/user-equipment-inventory/README.md) reports no external RF equipment; [measured recommendations](docs/research/measured-recommendations.md) defer same-signal sensitivity.
- [x] 2.3 Publish measured recommendations for continuous narrowband reception, 2.4 GHz observation and optional FPGA research. Proof: [measured recommendations and remaining RF limits](docs/research/measured-recommendations.md).

## Proof procedure

V4 stream procedure: `timeout --signal=INT 60s rtl_test -s RATE`, one device owner at a time, all stdout/stderr retained. Use rates 1024000, 2048000, 2400000 and 2560000; timeout termination is expected, not a tuner failure. RF and ESP comparison uses their saved manifests.

Required outcome: At least 60 seconds per V4 sample rate with lost-sample counts, plus measured ESP snapshot gaps. Each chosen application states the receiver, coverage, continuity and proof status.

## Accepted evidence and scope

Four physical trials each ran at least 65 seconds with complete receiver output,
exit code 0, cancellation and cleanup records. At 2.048 MS/s, one discontinuity
reported at least 80 bytes lost even though the integer-per-million summary
rounded to zero; the other trials had no reported discontinuities. This is an
internal-pattern USB test, not RF reception or an absolute loss-free guarantee.

The [fresh current-dipole FM/RDS trial](docs/evidence/rtl-dipole-rds/README.md)
records 287 directly valid PI blocks identifying WXJC at 101.1 MHz, with FEC
disabled. The user confirms the currently attached antenna is a dipole; its
model, dimensions and orientation are unverified. The selected station is
verified against its own published frequency. This establishes antenna
adequacy for this application, not all-band sensitivity.

The [equipment inventory](docs/evidence/user-equipment-inventory/README.md)
reports no external RF equipment. Task 2.2 explicitly permits deferring the
same-signal comparison when conversion/reference equipment is absent. No
sensitivity ranking is reported. The measured application matrix and
recommendations retain ESP snapshot-gap and RF-calibration limitations.

[Independent review](docs/evidence/rtl-dipole-independent-review/README.md)
replayed the fresh capture, rechecked all four transport trials and the ESP
matrix, and accepted all five original tasks and both requirements within
this scope. Same-signal sensitivity and FPGA integration remain unmeasured.
