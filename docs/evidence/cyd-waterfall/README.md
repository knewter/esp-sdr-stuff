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

## Install and host check (2026-10-06)

The build was written to the CYD at 460800 baud, and every region was
hash-verified. The CYD's original image stays preserved in `backups/cyd/`.
- **Boot:** the display code printed `#CYD panel ILI9341 id 18 02 06 00`.
  Those ID bytes match neither the usual ILI9341 reply nor the ST7789's
  `85 85 52`, so the panel type is still unconfirmed.
- **Host protocol:** the capture tool's queries returned the same `INFO`
  (`ESP32SDR 6 burst 16380`) and `LIMITS?` as the receiver image. A 20-window,
  16 MS/s capture at LO 2401 MHz completed 19 windows; one was lost to a UART
  fault and recovered, as in the session 004 and 005 captures under host load
  ([host-capture-results.json](host-capture-results.json)).

**Screen and touch are not yet shown.** They need a photo or video from the
board (tasks 2.1–2.3).
