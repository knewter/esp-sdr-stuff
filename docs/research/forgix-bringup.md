# Forgix identification and firmware preservation

This is a sourced bring-up recipe, not a measurement of the attached board. No USB, serial, SWD or FPGA interface was opened during this research. The board must be identified by its unplug/replug USB delta before a port or programmer is selected.

## First physical step

Use the Forgix USB-C connector with a known data cable, preferably on a direct host USB port. Record the USB descriptor/path delta when it is disconnected and reconnected. The [manufacturer describes that connector as power and programming](https://forgix.tech/). A lit LED proves neither working USB data nor a specific firmware. Custom firmware may use a non-Raspberry Pi descriptor, so absence of VID `2e8a` alone cannot identify or exclude the board.

## What enters boot mode

[Adiuvo's Adam Taylor describes the factory programmer and two boot-entry methods](https://www.hackster.io/adam-taylor/getting-started-with-forgix-4c72eb): request boot mode with picotool when compatible software enumerates, or hold the rear PROGRAM pad low while powering up. The on-board push button is attached to the FPGA; it is not a BOOTSEL button.

There is a material qualification. The [pinned Adiuvo schematic](https://bitbucket.org/adiuvo-engineering/forgix_public/raw/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/Schematic/RP2350_FPGA_eensy.pdf) routes PROGRAM to RP GPIO16, not QSPI chip select. The [RP2350 ROM boot sequence](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf), §5.2 (printed page 368), checks QSPI CSn, a watchdog boot request, or an optionally enabled RUN double tap. Thus the PROGRAM pad is not a demonstrated hardware ROM bypass.

The [factory source at the same revision](https://bitbucket.org/adiuvo-engineering/forgix_public/raw/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/BitStream_Loader/firmware/pico/src/main.c) contains no GPIO16 sampling or application boot-mode call. Its [CMake configuration](https://bitbucket.org/adiuvo-engineering/forgix_public/raw/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/BitStream_Loader/firmware/pico/CMakeLists.txt) enables SDK USB stdio. [Pico SDK 2.2.0](https://github.com/raspberrypi/pico-sdk/blob/a1438dff1d38bd9c65dbd693f0e5db4b9ae91779/src/rp2_common/pico_stdio_usb/include/pico/stdio_usb.h) enables its vendor reset interface by default. This supports investigating a targeted software boot request after identity is established, but neither the installed firmware nor physical PROGRAM-pad recovery is proven here. Confirm the board revision and recovery route before replacing RP firmware.

## Read-only factory identification

The [factory protocol](https://bitbucket.org/adiuvo-engineering/forgix_public/raw/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/BitStream_Loader/docs/protocol.md) has HELLO (`0x01`) and STATUS (`0x06`) commands that return current state without starting FPGA programming. A valid empty command uses the 20-byte little-endian header `FLDR`, version 1, the command type, flags 0, a sequence number, length 0 and CRC32 0. The matching ACK must retain its sequence, code, detail, byte count and message. This is only a candidate probe for a physically identified factory CDC device; never send it to a guessed ACM or FT232 port. START, DATA, END and ABORT can configure/reset the FPGA and do not belong to identification.

## Preserve before replacement

Use [Raspberry Pi picotool 2.3.1](https://github.com/raspberrypi/picotool/tree/2041936441b48a3cc53ae3da9e805229fe8f4e18), built with USB support. Select the identified bootloader's actual bus/address immediately before each command. `BUS` and `ADDRESS` below are placeholders, not discovered device values:

```sh
picotool info -a --bus BUS --address ADDRESS
picotool save -a -v backups/forgix-original-a.bin -t bin --bus BUS --address ADDRESS
picotool save -a -v backups/forgix-original-b.bin -t bin --bus BUS --address ADDRESS
picotool verify backups/forgix-original-a.bin -t bin --bus BUS --address ADDRESS
```

The upstream [save/verify documentation](https://github.com/raspberrypi/picotool/blob/2041936441b48a3cc53ae3da9e805229fe8f4e18/README.md#save) distinguishes full-flash `save -a` from its default program-only save. Confirm the observed capacity, both exact byte lengths, matching SHA-256 hashes and successful device comparison. Keep full flash and unsanitized device output in ignored private storage with restrictive permissions. Sanitize serial numbers and unique IDs before publishing receipts. A BOOTSEL drive is a loader interface, not evidence that its visible files constitute a firmware backup.

These read-only commands deliberately omit `-f`/`-F`: upstream defines those options as application-reset requests. An explicit, targeted boot request is a separate reversible operation. Do not erase flash, modify OTP, enable security, or load replacement firmware until preservation and the actual recovery route are verified.

## Tool preparation

A local host-only build pins picotool 2.3.1 commit `2041936441b48a3cc53ae3da9e805229fe8f4e18` and Pico SDK 2.2.0 commit `a1438dff1d38bd9c65dbd693f0e5db4b9ae91779`. Follow the [official build instructions](https://github.com/raspberrypi/picotool/blob/2041936441b48a3cc53ae3da9e805229fe8f4e18/BUILDING.md): configure with the SDK source path, USB support enabled and Release mode, then compile. This host build does not need a device or cross compiler. Missing mbedTLS disables signing/hashing features; USB information, save and verify remain available. A local tool build does not prove board enumeration, preservation, FPGA configuration or transport throughput.

The planned first FPGA experiment remains the [upstream CPU-less SPIBone identifier/scratch test](https://github.com/enjoy-digital/aduivo_forgix_test/tree/e7c71b750ca61690a70bc79ebd6ff5fbc65cedad). It requires actual MicroPython firmware, matching Efinity silicon/clock constraints, successful preservation and reversible configuration. Software cannot supply the external ESP-to-Forgix wiring.
