# Pinned original ESP32 firmware artifact

Host artifact verification, 2026-10-01. This record proves the acquired binary's
identity and integrity; it does not prove installation or RF performance.

- Source: [ESPARGOS esp-sdr at 550fadea](https://github.com/ESPARGOS/esp-sdr/tree/550fadea4d00a9e26ce921c5832167becb3dc20c).
- SDK: ESP-IDF `25fe69f946311abdaf9ad56591f25fedbc20ac98`.
- Build: [successful upstream GitHub Actions run 36905645289](https://github.com/ESPARGOS/esp-sdr/actions/runs/36905645289), artifact `firmware-esp32`, ID `11182889552`.
- Acquisition: `gh run download 36905645289 --repo ESPARGOS/esp-sdr --name firmware-esp32 --dir .scratch/firmware-esp32`.
- All three part lengths and SHA256 values match the artifact manifest; retained in [manifest.json](manifest.json).
- [esptool image-info](image-info.log) independently parses the application as chip ID 0 (ESP32), valid checksum and validation hash, project `esp_sdr`, version `550fade`, SDK `25fe69f9`, supported revisions 0.0–3.99.
- Upstream catalog marks 2 MB as a minimum; this board has 4 MB. Artifact default flash settings are DIO, 40 MHz, 2 MB header.
- Offsets: bootloader `0x1000`, partition table `0x8000`, application `0x10000`.
- Default runtime UART: 2,000,000 baud. Session `BAUD 1000000`/`BAUD 2000000` are supported. Boot returns to 2,000,000 baud.

The extracted part hashes establish integrity against the supplied manifest;
they are not an independent reproducible local build or a signature. The ZIP
archive digest has not been independently checked. Binaries remain in ignored
scratch storage, excluded from the public repository and site.

Protocol details are grounded in the pinned receiver and serial implementations:
[receiver.c](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c),
[burst_serial.c](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/common/burst_serial.c), and
[spectrum.c](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/common/spectrum.c).
`INFO` returns protocol identity and buffer limit, not a full firmware commit;
installed revision must be tied to the verified artifact and boot record.

Before installation, preserve all 4 MiB and the prior boot baseline. Upstream
initializes NVS and can erase its NVS partition if incompatible. The whole-chip
backup, not only the application, provides the restoration path.
