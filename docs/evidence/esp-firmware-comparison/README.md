# Offline comparison of the two UART receiver artifacts

This comparison reads existing binaries and build metadata only. It opens no device and provides no new reception evidence. The [numerical receipt](comparison.json) records exact part identities, per-segment hashes, sizes and byte-difference counts. Both sets of private binaries were independently rehashed against their manifests before comparison.

| Part | Bytes | Differing bytes | Location of differences |
| --- | ---: | ---: | --- |
| Bootloader | 25,792 | 54 | 21 build-descriptor bytes and 33 checksum/hash footer bytes |
| Partition table | 3,072 | 0 | Identical complete part |
| Receiver application | 664,608 | 85 | 52 application-descriptor bytes and 33 checksum/hash footer bytes |

The historical application's SHA-256 is `d7a2d80a70134b04e6078d5ac62b728e79ab33364c1845546f7ca321995e4685`; the Nix application's is `55aae718e026e26783693bcb2be455a8c0453922f3aff5c49e38817bf434c9f6`. The historical manifests and build metadata match the previously committed UART firmware receipts byte for byte. Full binary hashes differ, so each installation must retain its actual part hashes.

Both builds use receiver commit `550fadea4d00a9e26ce921c5832167becb3dc20c`, SDK commit `25fe69f946311abdaf9ad56591f25fedbc20ac98`, ESP-DSP commit `a53a0756833c045311ea1d79a2badf495cdfde4c`, and GCC `16.1.0_20260609`. Normalized configuration entries, including disabled options, match; the receipt records the raw configuration hashes too. Both use original ESP32, 921600 baud, 240 MHz and one FreeRTOS core.

All executable segments, writable-data segments, segment addresses and headers match. Every byte outside the application/bootloader descriptor and image footer matches. The descriptor differences are build date/time, SDK display label (`25fe69f9` versus the Nix packaging's `v6.2.0`), and the application's ELF digest. Both images' footer checksum and SHA-256 validation hashes were independently recalculated and verified.

The earlier historical-artifact 512-bin spectrum session completed 7,205 frames over approximately 60.005 seconds. Fresh demo trial 001 using the Nix artifact failed CRC after 205 valid-prefix frames; artifact-only trial 002 using the historical artifact also failed CRC, after 4,965 valid-prefix frames and 41.521749 seconds to the last accepted frame. Both used unchanged host software and RF/transport settings and both restored the original full flash and boot. These observations establish no cause for the failure and no reliability rate. Executable-byte and compiler identity prevent treating this as evidence of a changed compiler or changed receiver machine code. The next bounded intervention changes separately acquired FFT windows averaged per update from one to eight, while retaining the historical artifact and other RF/transport settings; any reduction in measured UART byte rate remains to be observed.

Espressif defines the descriptor layouts in the pinned [application descriptor](https://github.com/espressif/esp-idf/blob/25fe69f946311abdaf9ad56591f25fedbc20ac98/components/esp_app_format/include/esp_app_desc.h) and [bootloader descriptor](https://github.com/espressif/esp-idf/blob/25fe69f946311abdaf9ad56591f25fedbc20ac98/components/esp_bootloader_format/include/esp_bootloader_desc.h) headers. The primary receiver's [spectrum implementation](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/common/spectrum.c) constructs CRC-bearing snapshot frames; its [UART transport](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/common/burst_serial.c) sends them through the hardware FIFO with software waits and hardware flow control disabled. No transport fault is inferred from this source inspection alone.
