## 1. Measure the existing receiver

- [x] 1.1 Run 60-second sample-loss tests at 1.024, 2.048, 2.4 and 2.56 MS/s while the device is idle; retain complete output and stop/cleanup results. Proof: [physical transport measurements](docs/evidence/rtl-continuity/README.md).
- [ ] 1.2 Use an appropriate antenna and known source to verify one selected V4 application; publish receiver/source settings and a spectrogram or decoder result.

## 2. Compare useful capabilities

- [x] 2.1 Join the V4 continuity results and ESP acquisition/transfer timing into one application matrix; label local observations versus manufacturer/upstream claims. Proof: [measured application matrix](docs/research/measured-recommendations.md).
- [ ] 2.2 Inventory conversion/reference hardware before any same-signal RF test; if absent mark that comparison deferred rather than fabricate a ranking.
- [x] 2.3 Publish measured recommendations for continuous narrowband reception, 2.4 GHz observation and optional FPGA research. Proof: [measured recommendations and remaining RF limits](docs/research/measured-recommendations.md).

## Proof procedure

V4 stream procedure: `timeout --signal=INT 60s rtl_test -s RATE`, one device owner at a time, all stdout/stderr retained. Use rates 1024000, 2048000, 2400000 and 2560000; timeout termination is expected, not a tuner failure. RF and ESP comparison uses their saved manifests.

Required outcome: At least 60 seconds per V4 sample rate with lost-sample counts, plus measured ESP snapshot gaps. Each chosen application states the receiver, coverage, continuity and proof status.

## Current evidence and remaining gates

Four physical trials each ran at least 65 seconds with complete receiver output,
exit code 0, cancellation and cleanup records. At 2.048 MS/s, one discontinuity
reported at least 80 bytes lost even though the integer-per-million summary
rounded to zero; the other trials had no reported discontinuities. This is an
internal-pattern USB test, not RF reception or an absolute loss-free guarantee.

[The initial passive FM survey](docs/evidence/rtl-fm-survey/README.md)
recorded an unidentified 101.1 MHz candidate with 19 kHz structure.
[Subsequent no-FEC RDS evidence](docs/evidence/rtl-rds-trial/README.md)
and [independent replay](docs/evidence/rtl-rds-independent-review/README.md)
verify the selected WXJC application under the current receive path. Antenna
identity and attachment remain uninspected, so task 1.2 stays open pending that
physical inventory. The measured application matrix completes tasks 2.1/2.3;
conversion/reference equipment still requires physical inventory. No sensitivity
ranking or task 2.2 completion is claimed.
