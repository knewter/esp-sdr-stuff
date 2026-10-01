# Fresh preservation baseline

Evidence class: **Physical board UART capture**, October 1, 2026.

The confirmed CP2102 device was idle before inspection. [ROM identity](chip-and-flash.log) again reports ESP32-D0WD-V3 rev 3.1 and 4 MB physical flash. [Boot output](boot.log) shows the existing ESP-IDF `hello_world` program at 160 MHz and repeated all-pins toggling. [Capture metadata](capture.json) records the command and reset behavior.

No flash was written. The tool resets the chip through the UART bridge; this is not an independently demonstrated USB power-removal cycle. This record is the comparison baseline for later restoration.
