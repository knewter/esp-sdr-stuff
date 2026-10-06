# Cheap Yellow Display preserved and running ESP-SDR

Recorded 2026-10-06. The user's 2.8-inch ESP32 "Cheap Yellow Display" carries
an **ESP32-D0WD-V3 revision v3.1**, the same chip revision as the original
receiver board, with 4 MB of flash. It replaces the ESP32-C3 on the bench.

**USB.** The USB-C port did not enumerate, even on a USB-A to USB-C cable into
a USB-A hub port. The community documents missing CC resistors on that port.
The micro-USB port works and presents a CH340 (`1a86:7523`). A CH340 has no
unique serial number, so esptool's chip detection confirms the identity before
each use.

**Preservation came first.** Two full 4 MB reads are byte-identical (SHA-256
`e6728735…28fa`), and esptool's on-device verify against the first matched.
Two other reads aborted with corrupt data under heavy host load, and their
partial files were discarded. The board shipped with the stock LVGL Arduino
demo. The images and boot log stay private under ignored `backups/cyd/`.

**Receiver install.** The board now runs the same image the original ESP32 used
([manifest](../firmware-uart921600/manifest.json), `550fade-uart921600`). Every
part matched the manifest hashes and every region was hash-verified. `INFO`
answers `ESP32SDR 6 burst 16380`. The board offers 16, 40 and 80 MS/s, gain
0–72 and bandwidth 12–67, over UART at 921600.

At 16 MS/s, a 16380-sample snapshot covers 1023.75 µs, long enough for whole
BLE packets, unlike the C3's 80 MS/s windows. The capture tool now accepts the
CH340 as a receiver bridge. The other project's `1a86:55d2` dual-serial device
stays excluded.

**No reception is claimed yet.** This board's tuning offset is unmeasured; the
original board's ch37 offset (+1.7 to +2.4 MHz) does not carry over
automatically. Summary: [results.json](results.json).
