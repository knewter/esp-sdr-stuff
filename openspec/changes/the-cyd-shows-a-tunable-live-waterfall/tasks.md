## 1. Build

- [x] 1.1 Add `firmware/cyd-waterfall/`: `cyd_display.c`, a deterministic overlay onto a clean ESP-SDR `550fade` checkout, and a builder; build in `.#firmware` with UART 921600. Proof: [build record](docs/evidence/cyd-waterfall/README.md), with image hashes and an overlay diff limited to the display hooks.
- [x] 1.2 Host tests for the pure display logic (FFT row mapping, colour scale, touch-to-frequency mapping). Proof: `python3 -m unittest tests.test_cyd_waterfall_logic` (9 tests passing, including tone column, burst max-hold, DC removal and touch targets).

## 2. On-board proof (CYD, exclusive operator)

- [ ] 2.1 Install on the CYD (original image preserved) and confirm the waterfall updates with the frequency shown. Proof: a photo or video recorded in `docs/evidence/`. Progress: [panel-memory screenshots and measurements](docs/evidence/cyd-waterfall/README.md#beginner-screens-device-screenshots-and-measurements-2026-10-0607) from the device; the user reports the waterfall and touch working; a photo is still to be recorded.
- [ ] 2.2 Retune by touch and observe the displayed frequency change. Proof: a photo or video plus the serial status lines.
- [ ] 2.3 With the counted source on ch37, observe bursts near the board's measured ch37 carrier, absent with the source off. Proof: photos with source logs. Progress: [calibration](docs/evidence/cyd-waterfall/ble-calibration.json) — the detector finds 6/6 true packets offline, but on the device the source added no measurable rate over ~5% ambient activity.
- [x] 2.4 Confirm the host protocol queries and a 20-window capture still work on the display build. Proof: [host check](docs/evidence/cyd-waterfall/README.md#install-and-host-check-2026-10-06): INFO and LIMITS? unchanged, and 19 of 20 windows captured (1 UART fault recovered).
