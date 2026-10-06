## Context

The CYD is an original ESP32 (LX6, not S3), identical in chip revision to the
first receiver board. ESP-SDR's ESP32 backend
(`main/targets/esp32/receiver.c`) runs one loop that polls serial commands.
Its `acquire_iq()` fills a reserved 64 KiB SRAM aperture through the MAC dump
path.

## Boundaries

- **Firmware owns the display.** One extra file (`cyd_display.c`) and two
  hooks in the receiver loop. No host component is involved.
- **Radio access is shared, never concurrent.** Display ticks run only inside
  the receiver loop, between host commands, so acquisition is never re-entered.
- **Host owns its sessions.** Any received host line marks the host active.
  Display ticks stop until 5 s pass with no host traffic. Host `FREQ` and gain
  settings stay authoritative while the host is active.

## Display path

- **Panel:** ILI9341, 320×240 landscape, on HSPI (SCLK 14, MOSI 13, MISO 12,
  CS 15, DC 2, backlight 21). Driven through `esp_lcd` panel IO with plain DCS
  commands; no managed component, because the component manager stays
  disabled.
- **Touch:** XPT2046 on separate pins (CLK 25, MOSI 32, MISO 39, CS 33,
  IRQ 36), bit-banged at low speed.
- **Rows:** each tick acquires 16 MS/s IQ (4096 samples), takes 8 Hann-windowed
  512-point FFTs, and max-holds them so short bursts survive. The 512 bins map
  to 320 columns as a per-column maximum. The colour scale is set from a
  running noise-floor estimate.
- **Layout:** top bar with frequency, step and gain; touch buttons for −step,
  +step and step size (0.1/1/5 MHz); about 200 waterfall rows. A tap inside
  the waterfall retunes to the tapped column's frequency.

## Alternatives

- **Separate FreeRTOS display task:** rejected. It would need locking around
  `acquire_iq` and the PHY, and the receiver is single-loop by design.
- **ESP-SDR's SPEC FFT path:** its workspace and protocol framing are built
  for host transfer. A small local FFT keeps the host path byte-identical.
- **LVGL:** too large for the SRAM left beside the 64 KiB reserved aperture.
  A direct row blit is enough.

## Risks

- The tuning error depends on the LO (session 004: +2.5 MHz at 2401,
  −5.8 MHz near 2425), so the displayed frequency is the commanded LO, not a
  calibrated carrier.
- GPIO12 (panel MISO) is a flash-voltage strapping pin; the panel only
  drives it after boot.
