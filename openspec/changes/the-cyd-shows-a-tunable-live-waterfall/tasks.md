## 1. Build

- [ ] 1.1 Add `firmware/cyd-waterfall/`: pinned base files from ESP-SDR `550fade`, `cyd_display.c`, a deterministic overlay and a builder; build in `.#firmware` with UART 921600. Proof: build log, image hashes, and an overlay diff limited to the display hooks.
- [x] 1.2 Host tests for the pure display logic (FFT row mapping, colour scale, touch-to-frequency mapping). Proof: `python3 -m unittest tests.test_cyd_waterfall_logic` (9 tests passing, including tone column, burst max-hold, DC removal and touch targets).

## 2. On-board proof (CYD, exclusive operator)

- [ ] 2.1 Install on the CYD (original image preserved) and confirm the waterfall updates with the frequency shown. Proof: a photo or video recorded in `docs/evidence/`.
- [ ] 2.2 Retune by touch and observe the displayed frequency change. Proof: a photo or video plus the serial status lines.
- [ ] 2.3 With the counted source on ch37, observe bursts near the board's measured ch37 carrier, absent with the source off. Proof: photos with source logs.
- [ ] 2.4 Confirm the host protocol queries and a 20-window capture still work on the display build. Proof: a capture results.json.
