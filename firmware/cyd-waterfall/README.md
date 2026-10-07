# CYD on-screen waterfall

A Cheap Yellow Display build of the GPLv3-licensed
[ESPARGOS ESP-SDR revision 550fade](https://github.com/ESPARGOS/esp-sdr/tree/550fadea4d00a9e26ce921c5832167becb3dc20c).
It draws a live waterfall on the CYD's own screen and retunes by touch. Plan:
[OpenSpec change](../../openspec/changes/the-cyd-shows-a-tunable-live-waterfall/proposal.md).
The files here are distributed under the same GPLv3 terms.

- `src/cyd_waterfall_logic.{c,h}`: hardware-free logic, also compiled by
  `tests/test_cyd_waterfall_logic.py`. It covers 512-point FFT rows
  max-held over 8 blocks, the noise floor, the palette, column-to-frequency
  mapping and touch targets.
- `src/cyd_display.{c,h}`: the ILI9341/ST7789 panel (240×320 portrait, using
  hardware vertical scroll) and the bit-banged XPT2046 touch controller.
- `tools/build_cyd_waterfall.py`: copies a clean `550fade` checkout to fresh
  scratch, adds these files, inserts three exact-match hooks in
  `main/targets/esp32/receiver.c`, and builds with UART 921600. It never
  changes its input or the SDK.

## Screens

- **HOME:** four tiles (LIVE, WI-FI, BLUETOOTH, SETTINGS) and a HOW TO USE
  button. The radio idles here.
- **LIVE:** status (frequency, preset or `PC`/`PAUSED` badge, `EXT` outside
  2400–2500 MHz, gain and width), a readout (`STRONGEST …` or, after a tap,
  `HERE … HOLD=TUNE`), a scale with a magenta *expected zone* for BLE presets,
  the live spectrum and the waterfall.
  - The controls are `HOME`, `−`, `+` and `MORE`; `−` and `+` repeat while
    held.
  - Tap the graph to measure; hold for 0.6 s to tune there.
  - **MORE** opens a 5×3 grid:
    - presets: BLE 37/38/39, Wi-Fi 1/6/11 and 2.4 BAND;
    - settings: WIDTH (16/40/80 MHz), STEP, GAIN AUTO/MANUAL, GAIN −/+,
      COLOUR (20–50 dB), FLAT and PAUSE.
- **WI-FI:** an 80 MHz view centred on 2442 MHz.
  - Bars show each channel's busy share: the fraction of its central 16 MHz
    that sits 10 dB above that column's median.
  - The screen names the quietest of 1, 6 and 11 in words (QUIET, LOW, BUSY,
    VERY BUSY).
- **BLUETOOTH:** cycles channels 37/38/39 (1.5 s each, 16 MS/s) and counts
  narrowband bursts.
  - ch37/38 search ±2 MHz around this board's measured carrier; ch39 is
    unlocated, so its whole view counts.
  - Rates read as `HITS/MIN` (snapshot hits, not packets), with words
    thresholded at 5, 30 and 120.
- **SETTINGS:** FILTER (AUTO follows the width), COLOUR, GAIN mode and level,
  FLAT, TOUCH SETUP, RESET ALL (tap twice) and HOW TO USE.
- **HOW TO USE:** four pages.

The width, filter, gain, colour, step, preset, FLAT and last LIVE frequency
persist in NVS.

## Host commands

- **`CYDSHOT`:** streams the panel memory in display order (RGB666 plus a
  CRC).
- **`CYDSTAT`:** returns measurements as JSON.
- **`CYDSTATRESET`:** clears the measurements.
- **`CYDTAP x y ms`:** a virtual touch.

These commands do not pause the display; every other host line does.
`tools/cyd_device.py tour|shot|stat` uses them. Opening the CH340 port resets
the board.

## Simulator (not hardware evidence)

`tools/cyd_sim.py --output <dir>` compiles these sources with
`tests/cyd_sim/sim.c`, which emulates:
- an ILI9341 handling window, memory-write, continue, MADCTL, inversion and
  vertical-scroll commands;
- an XPT2046 answering the firmware's bit-banged reads;
- simulated time and NVS;
- a synthetic radio: noise, Wi-Fi channel 1 bursts, a CW spur, and BLE bursts
  where this board receives them.

It writes PNG screens of scripted scenarios and a contact sheet.
`tests/test_cyd_display_sim.py` drives the same simulator through user
interactions.

Build (no hardware): `nix develop .#firmware --command task firmware:cyd:build -- --source <clean 550fade checkout> --work .scratch/<fresh>`.
