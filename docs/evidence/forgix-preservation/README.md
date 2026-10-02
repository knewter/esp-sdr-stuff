# Forgix MCU flash preservation

**Pass: two independent reads of the detected 2 MiB RP flash range are byte
identical, separate device verification passes, and the original factory
application responds after returning from the ROM loader.** No flash write,
OTP change or FPGA configuration command was issued.

## Actual device and commands

A new USB device appeared on the user's Forgix connection: `2e8a:0009`,
product Pico, CDC serial `/dev/ttyACM2`, distinct from the CP2102 ESP and the
K230 dual-serial interface. Both [initial FLDR replies](initial-application.json)
pass response CRC and sequence checks. HELLO returns
`forge-loader rp2350 ready`; STATUS reports idle with zero bytes written.

The targeted software request `picotool reboot -u -f` succeeded. The same
physical USB path re-enumerated as `2e8a:000f`, RP2350 Boot.
[Sanitized ROM information](rom-info.txt) reports RP2350 revision A4, QFN60,
`forge_fpga_loader`, ARM Secure image, Pico SDK 2.2.0, board metadata `pico2`
and flash size 2048K. Image type is distinct from enabled secure boot;
ROM reports secure boot 0. These are MCU observations; FPGA grade,
PCB revision, oscillator and external wiring remain uninspected.

## Preservation proof

| Check | Result |
| --- | --- |
| First full-range `save -a -v` | Exit 0; 2,097,152 bytes; device comparison OK |
| Second independent `save -a -v` | Exit 0; 2,097,152 bytes; device comparison OK |
| Byte comparison and SHA-256 | Both identical: `72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4` |
| Separate `verify` against first file | Exit 0; device comparison OK |
| Application return `reboot -a` | Exit 0; original USB identity returns |
| Returned HELLO and STATUS | Both ACK, valid response CRC/sequence; factory loader ready and idle |

Pinned [picotool 2.3.1 source](https://github.com/raspberrypi/picotool/blob/2041936441b48a3cc53ae3da9e805229fe8f4e18/main.cpp)
implements `save -a` from flash start through its detected range. Its
`guess_flash_size` compares the first two pages at decreasing power-of-two
addresses to find address wrapping. Both info and full save use that same
heuristic: this preserves a detected range, not an independent JEDEC or
BOM capacity measurement. The saved address range is
`0x10000000` through `0x10200000` exclusive. Program-only binary end is much
smaller (`0x10006084`); these saves include the rest of the detected range.

Full binary files stay in ignored private `backups/forgix/`, mode 0600 inside
a mode-0700 directory. The [public receipt](receipt.json) records sizes,
hashes, timestamps, command options and terminal results. Raw device
identities are private. This preserves MCU flash only; OTP, volatile RAM
and any independently stored FPGA configuration are excluded.

## Return and limits

The [returned factory application](returned-application.json) responds to
HELLO/STATUS after the ROM round trip. No replacement image was installed,
so this proves software boot entry and application return, not a firmware
rewrite/restoration trial or physical BOOTSEL bypass. All serial handles
and short-lived device containers are closed.

Raw USB permissions prevented direct unprivileged picotool access. A
short-lived container exposed only the selected USB device node, read-only
pinned executable/libraries and the private backup directory. Networking
and capabilities were disabled; host USB permissions were not changed.
The [source-checked recipe](../../research/forgix-bringup.md) explains the
PROGRAM-pad and FPGA-button distinction.

No sustained FPGA transport, clock measurement, pin voltage, external ESP
wiring or RF integration is proven by these MCU operations. The FPGA
proposal remains open pending physical inventory and benchmark evidence.

[Independent review](../forgix-preservation-review/README.md) reproduces both
private backup hashes, raw FLDR reply checks and each successful tool receipt,
and verifies public sanitization and the stated preservation limits.
