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

## Patched ESP-IDF trial: boots, then hangs in Wi-Fi init

A bounded trial on 2026-10-06 tested whether a patched ESP-IDF v6.2 could run
ESP-SDR on this ECO1 engineering sample.

**Desk research**
- ESP-IDF dropped ECO1 support when the ECO2 ROM landed (merge `16d79103aa`,
  2025-04-16). The ECO2-only Wi-Fi libraries followed a day later. The last
  master commit with ECO1 support is `d930a386da`.
- Comparing ROM linker scripts: none of the 1287 shared symbols changed
  address. Of the 1113 ROM symbols v6.2 links, 84 are missing from ECO1: 25
  are renames at identical addresses, and 59 are new in the ECO2 ROM, mostly
  Wi-Fi `pp`/`net80211` code.

**The patch** ([idf-v62-eco1-trial.patch](idf-v62-eco1-trial.patch)) changes
six files:
- a `REV_MIN 0` Kconfig choice;
- the 59 ECO2-only ROM symbols commented out;
- a fallback bootloader offset;
- RAM copies of three pointers that ECO1 does not have in ROM.

**Result.** ESP-SDR linked, flashed and hash-verified. The v6.2 bootloader,
IDF startup, heap, flash, NVS and USB driver all ran on the v0.2 chip.
**`esp_wifi_init()` then hung** right after printing the ROM `pp`/`net80211`
versions: the RTOS tick stopped and the task watchdog fired repeatedly. The
receiver never answered the protocol. The cause is v6.2's binary Wi-Fi
libraries, which expect the ECO2 ROM's Wi-Fi code. Linker scripts cannot fix
that.

**Restored.** The original image was written back. On-device verify matched
`890327ac…96fc`, and the original `iperf` firmware booted again.

**Remaining route.** Build ESP-SDR against ESP-IDF `d930a386da` with its
matching ECO1 Wi-Fi and PHY libraries. That needs a second IDF input with its
own toolchain and Python environment, porting any v6-only API uses, and
re-checking C5 tuning on ECO1. It would be an unsupported build on an
engineering sample, so the C3 or a production C5 is the better receiver.
