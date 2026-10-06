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

## Behaviour

- **Display mode.** It runs only while the host has been silent for 5 s. Any
  host line pauses it, and host replies and captures are those of the
  `550fade` receiver.
- **Waterfall.** Each row comes from one 4096-sample, 16 MS/s snapshot and
  spans LO ±8 MHz across 240 columns. Rows arrive every 40 ms or slower, with
  gaps between snapshots. The top of the screen holds the commanded LO,
  which is **not** a calibrated carrier: session 004 measured LO-dependent
  offsets on this board.
- **Touch controls:**
  - `−` and `+` step the LO;
  - `STEP` cycles 1, 5 and 10 MHz;
  - a tap in the waterfall retunes to that column (whole MHz);
  - a tap on the frequency line toggles panel colour inversion.
- **Serial status.** Touches print `#CYD touch …` and `#CYD freq …`, and boot
  prints the detected panel. A host's SYNC fence discards these lines.

Build (no hardware): `nix develop .#firmware --command task firmware:cyd:build -- --source <clean 550fade checkout> --work .scratch/<fresh>`.
