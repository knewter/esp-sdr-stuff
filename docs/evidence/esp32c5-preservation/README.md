# ESP32-C5 board preserved before any SDR trial

Recorded 2026-10-06. The user's ESP32-C5-DevKitC-1 identifies as an
**ESP32-C5 revision v0.2** (ROM `esp32c5-eco1-20240726`, 48 MHz crystal,
240 MHz) with **8 MB** of flash. It shipped running Espressif's `iperf` demo on
ESP-IDF v5.5-dev.

**Two full 8 MB reads are byte-identical** (SHA-256 `890327ac…96fc`), and
esptool's on-device verify against the first copy matched. The images and the
original reset-boot log stay private under ignored `backups/esp32c5/`.

Reading over the chip's native USB (USB-Serial/JTAG) failed. With esptool's
flasher stub the writes timed out, and without it the ROM loader stopped after
8 KB. Both read paths were unreliable with the pinned esptool, so preservation
used the board's on-board CP2102N USB-to-UART bridge. A udev rule now keeps
ModemManager off Espressif native-USB devices.

## Receiver build: this chip revision is not supported

ESP-SDR `550fade` builds cleanly for `esp32c5` with the pinned ESP-IDF
(`25fe69f9`, v6.2), using a new `.#firmware-riscv` shell. **esptool refused the
install before writing anything**: the bootloader requires chip revision
v1.0–v1.99, and this board is **v0.2**. That ESP-IDF supports only C5 v1.0
(ECO2) and v1.2; v0.x engineering samples are no longer supported, and ESP-SDR's
C5 radio backend targets production silicon. The board needs a production
ESP32-C5 (revision 1.0 or later) to work as a receiver.

Nothing has been written to the C5. Any receiver trial must restore this image
and confirm the `iperf` reset boot afterwards. Summary: [results.json](results.json).
