# FPGA inventory and provenance

Evidence class: **Host enumeration plus attributed local notes**, October 1, 2026.

The user identifies their external board as an **Adiuvo Forgix**. It was not physically inspected in this session. [Adiuvo's official design](https://forgix.tech/) lists RP2354, Efinix Trion T8F49, 7,384 logic elements, PSRAM and USB 1.1. These are design specifications, not measurements of this user's board.

The read-only command `lspci -nn -s 05:00.0` returns:

```text
05:00.0 Ethernet controller [0200]: Device [dabc:1017]
```

Unprivileged verbose inspection reports BAR0 2 KiB and BAR2 512 MiB, with access to extended capabilities denied. A PCI BAR address window is not a measurement of available FPGA RAM.

Neighboring `fpga-research-site` documentation associates this identity with Alibaba Cloud AS02MC04, silkscreen R1291-F9003-02 and Kintex UltraScale+ XCKU3P-2FFVB676I, and reports no external DRAM. These details are attributed to existing local research (whose README declares CC BY 4.0), not independently verified physical identification in this session. No images or research text were copied.

No device driver, PCIe DMA, JTAG programming, FPGA configuration or RF integration was attempted. First tasks: verify card markings and connectors, then establish a reversible bring-up path and measured synthetic transport.
