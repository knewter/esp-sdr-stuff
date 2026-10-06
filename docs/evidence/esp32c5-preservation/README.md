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

The next section takes the remaining route.

## Last ECO1-era ESP-IDF: ESP-SDR runs

A second trial on 2026-10-06 built ESP-SDR against ESP-IDF `d930a386da`, the
last commit that supports ECO1, **and it works**.

**Toolchain.** [eco1-idf.nix](eco1-idf.nix) overrides the
nixpkgs-esp-dev revision that the repo flake locks:
- ESP-IDF at that commit, with its ECO1 PHY and Wi-Fi libraries;
- GCC 14.2.0 (`esp-14.2.0_20241119`);
- the matching Python environment.

The expression lives in scratch only and permits an old `ecdsa` package that
esptool 4.x needs. No global installs.

**ESP-SDR port** ([esp-sdr-eco1-port.patch](esp-sdr-eco1-port.patch)). No API
porting was needed; two things were:
1. **Link flag.** The ECO1 `librftest.a` defines `phy_enter_critical` and
   `phy_exit_critical` a second time. `--allow-multiple-definition` keeps
   ESP-IDF's copy.
2. **Patched vendor capture routine.** The first stock capture crashed the CPU
   (`CPU_LOCKUP`). The cause is the ECO1 blob's `adctrig`: it gives SRAM bank 2
   to the RF dump, and that bank holds heap and stacks. The v6.2 blob uses
   bank 1, which ESP-SDR reserves. A copy of `mac_common.o` with exactly two
   instructions changed to point at bank 1 fixes it. The patched object is a
   modified Espressif binary, so it is not published; the diff describes it.

**Protocol at 2 Mbaud over the CP2102N.** `INFO` answers
`C5SDR 6 burst 16380`. The firmware reports:
- **6 rates: 80, 40, 20, 10, 8 and 4 MS/s**;
- 8- and 10-bit samples;
- gain 0–79 with hardware AGC;
- bandwidth 11–48;
- snapshot spectra at 256–2048 bins.

**First IQ.** Each row is 10 windows of 16380 10-bit samples at 20 MS/s
(819 µs each). All 40 windows passed CRC.

| Setting | Median power (codes²) | Behaviour |
| --- | ---: | --- |
| 2412 MHz, hardware gain | 5314 | about 400 unique codes per component |
| 2412 MHz, manual gain 0 | 8 | almost silent |
| 2412 MHz, manual gain 40 | 42 | bursty, 8 to 17,962 |
| 2300 MHz, manual gain 40 | 47 | steady, AC power 3.7 |

At the same fixed gain, Wi-Fi channel 1 is bursty while the off-band 2300 MHz
setting is a steady floor. That points to real in-band reception, but it is
not a calibrated test.

**Restored.** On-device verify matched `890327ac…96fc`, and the iperf firmware
booted again.

**What it means.** The engineering sample can be a receiver, through an
unsupported IDF snapshot and one patched vendor object. It offers lower rates
than the C3: at 20 MS/s a window lasts 819 µs, long enough for whole BLE
packets. Untested so far: tuning accuracy, the 5 GHz band, and reception of
a known source. Each needs a pre-declared trial.
