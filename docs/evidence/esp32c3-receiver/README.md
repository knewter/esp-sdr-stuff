# ESP32-C3 preserved and running ESP-SDR

Recorded 2026-10-06. The user's ESP32-C3-MINI-1 board identifies as an
**ESP32-C3 (QFN32) revision v0.2** with 4 MB of embedded flash, reached through
its on-board CP2102N USB-to-UART bridge. It replaces the original ESP32 on the
bench.

**Preservation came first.** Two full 4 MB reads are byte-identical (SHA-256
`cd351747…1a08`), and esptool's on-device verify against the first copy
matched. The images stay private under ignored `backups/esp32c3/`. The
original firmware's boot log was not captured before the install; restoring
the image reproduces it.

**The receiver install worked without hacks.** Unlike the C5 engineering
sample, revision v0.2 is a stock ESP-IDF option. ESP-SDR `550fade` was built
for `esp32c3` with the pinned ESP-IDF (`25fe69f9`) and one extra setting,
`CONFIG_ESP32C3_REV_MIN_2=y`, then written and hash-verified region by region.

**First contact over UART0 at 2 Mbaud** (more than twice the original ESP32's
921600-baud CP2102 link): `INFO` answers `C3SDR 6 burst 16380`. The firmware
reports 8- and 10-bit snapshots at **80 MS/s only**, 14–62 MHz analog
bandwidth, gain 0–79 with hardware AGC, and snapshot spectrum profiles of
256–2048 bins.

**No reception is claimed yet.** No RF capture has been taken. At 80 MS/s a
16380-sample snapshot covers 204.75 µs, against 1023.75 µs at the original
ESP32's 16 MS/s, so the BLE decoder and the capture tool (which expects
`ESP32SDR`) need adapting first. Summary: [results.json](results.json).
