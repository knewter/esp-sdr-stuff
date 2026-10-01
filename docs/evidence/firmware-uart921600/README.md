# Clean original ESP32 firmware at 921600 baud

Local build verification, 2026-10-01. This configuration-only artifact addresses
the classic CP2102's documented default baud table. Physical protocol/capture
results are recorded separately by the board operator.

The source is unchanged at
`550fadea4d00a9e26ce921c5832167becb3dc20c`, SDK unchanged at
`25fe69f946311abdaf9ad56591f25fedbc20ac98`, ESP-DSP remains
`a53a0756833c045311ea1d79a2badf495cdfde4c`. Target is original `esp32` at
240 MHz with the upstream single-core configuration. Generated defaults change
only UART from 2,000,000 to **921600**; application version is
`550fade-uart921600`. There are no diagnostic markers or source-code patches.

The [Silicon Labs CP2102/9 datasheet](https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf)
lists standard rates up to 921600. Manufacturer
[AN205 rev.0.4, archived primary document](https://www.freecalypso.org/pub/GSM/Pirelli/chips/silabs_an205.pdf)
Table1 maps requests from 670255 through 1053257 to physical 921600; its
page6 example explains that a separate 1 Mbaud physical rate needs EEPROM
alias customization. Linux's host-side 1 Mbaud cap/termios acceptance therefore
does not establish a physical 1 Mbaud rate. This experiment changes firmware
configuration rather than the bridge EEPROM.

Build receipt: [build-info.json](build-info.json).
Flash manifest: [manifest.json](manifest.json).
Independent image parsing: [image-info.log](image-info.log).
Every part size/SHA256 was independently checked against the exported manifest.
The app parser confirms a valid ESP32 image, supported chip revisions 0.0–3.99,
version `550fade-uart921600`, SDK `25fe69f9`, checksum and validation hash.
Flash offsets/settings stay bootloader `0x1000`, partition `0x8000`, app
`0x10000`, DIO/40 MHz/minimum 2 MB header. Binary parts stay ignored.

Reproduction after activating the pinned SDK:

```sh
python tools/build_esp_sdr_uart.py \
  --source .scratch/esp-sdr --sdk .scratch/esp-idf \
  --build .scratch/build-esp32-uart921600 \
  --output .scratch/firmware-esp32-uart921600 \
  --evidence docs/evidence/firmware-uart921600 \
  --baud 921600 --jobs 6
```

Use `--baud 921600 --firmware-revision 550fade-uart921600` for the host snapshot
harness and `--baud 921600` for the UART browser bridge. Build success is not
accepted RF behavior; measured UART replies and CRC-checked captures prove that
separately. Nominal ADC sample rate remains independent from UART baud.
