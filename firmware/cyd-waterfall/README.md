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

## Screen

| Region | Height | Content |
| --- | --- | --- |
| Status | 32 px | Tuned LO (large); a badge (`HOST` while the PC owns the radio, `FROZEN`, or the active preset); `EXT` outside 2400–2500 MHz; gain and span; live peak readout (`PK 2426.3 +18DB`) and, with a marked BLE channel, a burst counter |
| Scale | 12 px | Absolute MHz ticks at ±3/8 and ±3/16 of the span; magenta marker where this board's channel lands (`?` if not yet measured) |
| Spectrum | 48 px | Live trace (palette-filled, white edge), decaying peak-hold (yellow), grid, marker |
| Waterfall | 172 px | Newest row on top, scrolled by the panel's own registers |
| Controls | 56 px | `−` and `+` (repeat while held), `STEP` (1/5/10 MHz), `MENU` |

Tapping the spectrum or waterfall retunes to that column.

**MENU** replaces the waterfall with a 5×3 grid:
- **Band presets:**
  - **BLE 37 and BLE 38** tune to LO 2401 and 2425 MHz at 16 MHz span and mark where sessions 004/005 found the carrier: +3.3 MHz for ch37 and −5.9 MHz for ch38, relative to the LO.
  - **BLE 39** marks the nominal channel with `?`, since ch39 is still unlocated.
  - **Wi-Fi 1/6/11** use a 40 MHz span.
  - **2.4 BAND** shows 2402–2482 MHz at once, at the 80 MHz span.
- **Receiver settings:**
  - **SPAN** cycles 16/40/80 MHz, the ESP32's hardware sample rates.
  - **FILT** cycles AUTO/12/20/40/67 MHz (the `BANDWIDTH` command).
  - **GAIN** switches between AGC and manual, with −/+ in steps of 4.
  - **RANGE** sets the colour range: 20/30/40/50 dB above the floor.
  - **FREEZE**, and **CLOSE**.

Presets close the menu; settings stay open so they can be combined.

## Behaviour

- **Display mode.** It runs only while the host has been silent for 5 s. Any
  host line pauses it and shows `HOST`. Host replies and captures are those of
  the `550fade` receiver. When the host leaves, the display picks up its
  frequency, gain and filter.
- **Rows.** Each row comes from one 4096-sample snapshot (256 µs at 16 MS/s,
  51 µs at 80 MS/s), with gaps between snapshots. Columns max-hold eight
  512-point FFTs, so short bursts survive. The frequency shown is the
  commanded LO, **not** a calibrated carrier. Session 004/005 offsets are
  LO-dependent, and the markers apply only at their preset LOs.
- **Touch.** The firmware carries this board's touch calibration (measured
  2026-10-06). Holding a finger on the screen at power-up runs a three-cross
  calibration, which is stored in NVS.
- **Serial status.** Boot prints the detected panel, and retunes print
  `#CYD freq …`. A host's SYNC fence discards these lines.

Build (no hardware): `nix develop .#firmware --command task firmware:cyd:build -- --source <clean 550fade checkout> --work .scratch/<fresh>`.
