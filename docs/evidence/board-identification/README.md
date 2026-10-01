# Original ESP32 identification

Evidence class: **Board capture**. Recorded October 1, 2026 by a fresh, read-only inspection.

- [Chip and flash query](chip-and-flash.log): ESP32-D0WD-V3 revision 3.1, dual cores, capability up to 240 MHz, 40 MHz crystal, 4 MB physical flash.
- [Boot log](boot.log): ESP-IDF v5.4-dirty; project hello_world; current CPU 160 MHz; repeated all-pins toggling. AtomVM startup was not observed.
- [Capture metadata](capture.json) records the time, command, baud, reset behavior and redaction.

The unplug/replug survey removed and restored only the CP2102 device that originally used ttyUSB0. The dual-serial ACM adapter remained present.

Reproduce: `/usr/bin/python3 tools/inspect_board.py --port SELECTED_PORT --output docs/evidence/board-identification`.

Limitations: the ROM query and UART opening reset the board but do not write firmware. The MAC address is redacted. The boot image declares 2 MB even though the physical flash is 4 MB. Development-board brand, module label, antenna layout and fitted PSRAM have not been identified. No SDR firmware has been installed and RF reception is untested.
