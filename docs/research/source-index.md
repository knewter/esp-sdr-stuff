# Source register

Reviewed October 1, 2026. Claims from upstream are distinct from board observations. Repository links are pinned where possible.

## The discovery

[News / starting point](https://www.rtl-sdr.com/various-projects-independently-find-hidden-sdr-capabilities-in-esp32-microcontrollers/)

Links the independent ESPARGOS, eSpDR and C5VRX discoveries.

Limit: Published October 1, 2026. A project summary, not a measurement of our hardware.

## ESPARGOS · ESP-SDR

[Primary / firmware](https://github.com/ESPARGOS/esp-sdr/tree/550fadea4d00a9e26ce921c5832167becb3dc20c)

Original ESP32 is supported. Current firmware provides raw I/Q bursts and snapshot FFTs on this chip.

Limit: Minimum 2 MB flash. Support does not prove reception on this particular board.

## Receive controls

[Primary / limits](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/docs/rx-controls.md)

ESP32 filter mapping is approximately 12–67 MHz. Extended tuning commands are attempts, not validated coverage.

Limit: Gain is uncalibrated; PLL lock and RF accuracy are not guaranteed outside the normal band.

## Original ESP32 capture path

[Primary / code](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c)

Reserves 64 KiB; at most 16,380 pairs per snapshot; nominal 16/40/80 MS/s with 8/10-bit packed output.

Limit: Small sample windows and UART transfers produce gaps. Nominal sample rates are not clock calibration.

## This board's serial bridge

[Primary / CP2102/9 data sheet](https://www.silabs.com/documents/public/data-sheets/CP2102-9.pdf)
and [Silicon Labs AN205](https://www.freecalypso.org/pub/GSM/Pirelli/chips/silabs_an205.pdf).

The classic CP2102 has default baud-rate aliases; requesting 1 Mbaud can map to
921,600 without custom EEPROM configuration. Host termios acceptance alone does
not prove the physical wire rate. Our clean 921,600-baud firmware returns valid
commands and CRC-checked snapshots; the 2 Mbaud and 1 Mbaud trials did not.

Limit: No bridge EEPROM was changed. The failed trials do not measure actual
wire baud and do not establish an RF or silicon failure. See
[physical transport trial](docs/evidence/sdr-installation-uart921600/README.md).

## Spectrum protocol & validation

[Primary / FFT behavior](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/docs/spectrum.md)

Original ESP32 uses snapshot FFTs. Selected newer chips can keep RF capture running while processing selected windows.

Limit: Continuous spectrum updates are not the same as exporting every I/Q sample.

## ESPARGOS discovery notes

[Primary / overview](https://espargos.net/espsdr/)

Uses the internal modem ADC path. Reports experimental coverage around 2.2–2.7 GHz and coherent multi-receiver arrays.

Limit: Do not transfer array capabilities to one dev board or treat historical S31 transport plans as current firmware features.

## eSpDR · continuous FPGA transport

[Primary / reference design](https://github.com/h0m3us3r/eSpDR/tree/41a0ffe279119df942e4a9e892dc19d196e1c952)

ESP32-S3, two GPIO lanes, Artix-7 FPGA, DDR buffer and FT600 USB 3 support an 80 MS/s path.

Limit: Uses S3 dedicated GPIO and SIMD. The original LX6 board cannot use this firmware unchanged. Current clocking forwards an ESP-generated clock to the FPGA.

## C5VRX · 5.8 GHz video

[Primary / separate platform](https://github.com/Twotoz/C5VRX/tree/8dcc7e41c5e13e8d4c078878e250a17341df9930)

ESP32-C5 receives analog FPV and demodulates in the hardware pipeline, with composite video via resistor DAC.

Limit: Requires C5 radio and peripherals. Bench results do not establish range performance; not supported on our ESP32.

## Espressif ESP32 datasheet

[Primary / silicon specification](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf)

Dual LX6 up to 240 MHz, 520 KB SRAM, a 2.4 GHz radio and SPI/I2S/GPIO interfaces.

Limit: Chip capability is not an inventory of board wiring, antenna connector or fitted external RAM.

## RTL-SDR Blog V4 design

[Primary / receiver manufacturer](https://www.rtl-sdr.com/rtl-sdr-blog-v4-dongle-initial-release/)

R828D with built-in HF upconverter, 500 kHz lower coverage, upper range around 1.766 GHz, filtering, SMA and 1 ppm TCXO.

Limit: Coverage and oscillator specifications are manufacturer claims; our probe establishes identity, not sensitivity or tuning accuracy.

## RTL-SDR sampling & applications

[Primary / manufacturer documentation](https://www.rtl-sdr.com/about-rtl-sdr/)

8-bit I/Q, continuous USB streaming; 2.4 MS/s is a useful starting rate. Supports many narrowband demodulators.

Limit: High sample rates can lose samples; measure sustained delivery on this host. Both stock receiver configurations are receive-only.

## AtomVM programming guide

[Primary / runtime integration](https://www.atomvm.net/doc/master/programmers-guide.html)

Native extensions and ports provide integration boundaries for low-level work.

Limit: No ready-made ESP-SDR binding has been verified here. Do not run high-rate I/Q handling in ordinary Erlang processes.

## OpenSpec workflow

[Primary / planning](https://openspec.dev/docs)

Proposal, delta specs, design and tasks describe planned changes; archiving records accepted capabilities.

Limit: Installed CLI is 1.11.0. This site adds evidence-aware tracking copied from the local T-Display-K230 project.

## Adiuvo Forgix

[Official board](https://forgix.tech/): RP2354, Efinix Trion T8F49 (7,384 logic elements), PSRAM and USB 1.1, with 3.3 V I/O. [Primary LiteX demonstration](https://github.com/enjoy-digital/aduivo_forgix_test) provides a bounded SPI development route. Actual board revision, pinout and firmware remain inventory tasks. USB-C is a connector description; it does not establish USB 3 transport.

The [FPGA inventory](../evidence/fpga-inventory/README.md) distinguishes host enumeration from attributed prior PCIe-card research.
