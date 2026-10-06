# CYD on-screen waterfall

Plan: [OpenSpec change](../../../openspec/changes/the-cyd-shows-a-tunable-live-waterfall/proposal.md).
Source: [firmware/cyd-waterfall](../../../firmware/cyd-waterfall/README.md).

## Build (2026-10-06, host only)

`tools/build_cyd_waterfall.py` built ESP-SDR `550fade` (esp-dsp `a53a075`)
with the overlay in the locked `.#firmware` shell. The configuration is
UART 921600 and the version is `550fade-cyd-waterfall`.
- **Build:** clean, with no compiler warnings from the display sources. The
  app partition has 33% free.
- **Image hashes:** in [build-info.json](build-info.json). Flash with dio,
  40 MHz, 2 MB at 0x1000, 0x8000 and 0x10000.
- **Changes to the receiver:** limited to one include, the wrapper
  functions over the existing static radio routines, an init call and the two
  idle/host-activity calls ([receiver-hooks.diff](receiver-hooks.diff)). CMake
  adds the two sources and the `esp_lcd`, SPI and GPIO driver components for
  the ESP32 target only.
- **Host tests:** `tests/test_cyd_waterfall_logic.py` compiles the logic file
  and runs 9 tests, all passing.

**Not yet shown on hardware.** The board has not run this build. The panel
type (ILI9341 or ST7789), its orientation and the touch calibration are
unverified until the first install.
