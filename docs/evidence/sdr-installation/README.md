# First SDR installation and UART limit

Evidence class: **Physical flash write, boot capture and host UART probes**, October 1, 2026.

After [verified preservation](../firmware-preservation/README.md), the pinned upstream original-ESP32 artifact was written at its documented offsets. [Write output](write.log) verifies each part's flash hash; [installation manifest](manifest.json) ties those parts to the source revision.

[Boot at 115200](boot-115200.log) identifies `esp_sdr`, version `550fade`, SDK `25fe69f9`, original ESP32 rev 3.1 and a single-core 240 MHz application. This proves application startup, not completed radio initialization or reception. The initial [garbled 2 Mbaud probe](baud-2000000-garbled.log) is failed transport evidence, not a valid boot transcript.

[UART probes](uart-probes.json) show requested 2,000,000 baud is clamped to 1,000,000 in Linux termios. The upstream receiver defaults to 2 Mbaud, so it cannot negotiate a lower session baud through this bridge. Two SYNC probes failed; no RF or I/Q claim follows from these timeouts. [Linux's primary cp210x driver](https://github.com/torvalds/linux/blob/master/drivers/usb/serial/cp210x.c) documents the classic chip's rate limit. A [configuration-only 1 Mbaud build](../firmware-uart1m/README.md) follows.

The original image was subsequently restored and independently reread: [restoration record](../first-restoration/README.md). Experimental firmware is explicitly authorized by the active user goal. No eFuse, transmitter or FPGA was programmed.
