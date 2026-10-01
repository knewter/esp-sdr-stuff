# Original ESP32 firmware with a 1 Mbaud default

Local build verification, 2026-10-01.

**Subsequent source review:** accepting a 1 Mbaud request in kernel termios does
not prove a physical 1 Mbaud UART. Silicon Labs
[AN205 default alias table](https://www.freecalypso.org/pub/GSM/Pirelli/chips/silabs_an205.pdf)
maps a 1 Mbaud request to 921600 unless the bridge EEPROM has been customized.
This historical variant is not a working-transport acceptance record; the clean
921600 variant is the next compatibility trial. No EEPROM was changed.
 This is a configuration variant of the
pinned upstream receiver, built to accommodate the board's classic CP2102
transport. It is not a binary patch and does not itself prove installation or RF.

The upstream image defaults to 2 Mbaud. Linux's
[cp210x driver](https://github.com/torvalds/linux/blob/master/drivers/usb/serial/cp210x.c)
limits a classic CP2102/CP2103 to 1 Mbaud and clamps requested rates. A running
2 Mbaud receiver cannot negotiate a session change through a bridge transmitting
at 1 Mbaud. The corrective build sets its boot-time transport to 1 Mbaud.

- Receiver source: `550fadea4d00a9e26ce921c5832167becb3dc20c`.
- ESP-IDF: `25fe69f946311abdaf9ad56591f25fedbc20ac98` (6.2 development SDK).
- Compiler: Espressif Xtensa GCC 16.1.0, tool release `esp-16.1.0_20260609`.
- ESP-DSP submodule: `a53a0756833c045311ea1d79a2badf495cdfde4c`.
- Target: original `esp32`, 240 MHz, firmware configured single core.
- Source code remains unchanged. Generated defaults change only
  `CONFIG_ESP_SDR_UART_BAUD=2000000` to `1000000`; CMake sets application
  version `550fade-uart1m` to distinguish the configuration variant.
- [Build/configuration provenance](build-info.json), [flash manifest](manifest.json),
  and [independent image parsing](image-info.log) retain exact revisions and hashes.
- Flash settings remain DIO, 40 MHz, minimum 2 MB header; offsets remain
  bootloader `0x1000`, partition `0x8000`, application `0x10000`.

Reproduction uses [tools/build_esp_sdr_uart.py](../../../tools/build_esp_sdr_uart.py)
after installing and activating the pinned SDK environment:

```sh
python tools/build_esp_sdr_uart.py \
  --source .scratch/esp-sdr --sdk .scratch/esp-idf \
  --build .scratch/build-esp32-uart1m \
  --output .scratch/firmware-esp32-uart1m \
  --evidence docs/evidence/firmware-uart1m \
  --baud 1000000 --jobs 6
```

All outputs were built successfully and exported. Every artifact part's size
and SHA256 were independently compared with the exported manifest. The
application parser confirms chip ID 0, valid image checksum/validation hash,
version `550fade-uart1m`, SDK `25fe69f9`, and supported revisions 0.0–3.99.

Downloads, SDK, build logs and binary parts remain in ignored scratch storage.
Use `--baud 1000000` for host capture/browser bridge. The snapshot tool's
`--firmware-revision 550fade-uart1m` labels the variant; installation evidence
must connect that asserted revision to the actual boot and flashed hashes.

No accepted RF capability or hardware task is marked complete by this build
record. Preservation and restoration have their own physical evidence.
