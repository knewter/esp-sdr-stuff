# RP2350 RAM-only producer: offline build checkpoint

Build 004 completed all 82 Ninja steps under the locked Nix
`forgix-usb-ram` shell, with two build jobs, from committed source
`0beff50d69ef5cb69939815f9c879a9d84a33678`. The actual ELF passes the
layout guard. No device was opened and no image was loaded. This is a synthetic
MCU USB producer; it proves neither FPGA transport nor electrical safety,
throughput, enumeration, watchdog recovery or a hardware acceptance gate.

The application uses one direct TinyUSB owner, a 16-record queue and distinct
nonce/sequence/length/timestamp/payload-CRC framing. It permits one 60-second
run, a fixed two-second drain and a 120-second maximum main lifetime. A two-second
watchdog starts before USB initialization; an initialization failure stops
feeding. Earlier callbacks do not establish END delivery. Host-delivered counts
and physical recovery require a separate collector and reviewed lifecycle.

Actual allocations total 35,948 bytes, including a 4,096-byte core0 stack;
core1 stack and heap reservations are zero. Both LOAD physical/virtual ranges
are ordinary SRAM; all executable bytes, Thumb entry, initial SP and RP2350
RAM IMAGE_DEF metadata were inspected. The guard checks layout and selected
symbols, not arbitrary instruction behavior. Eight mutations of the actual ELF
reject flash/peripheral destinations, dynamic/interpreter segments, invalid
entry/SP, excess allocation and a profile present only outside LOAD bytes.
All exported hashes match the private manifest. Thirteen focused tests pass.

Linked-code self-audit: `main` starts at `0x200010d0`; watchdog initialization
is called at `0x200010ec`, USB initialization at `0x200010f8`, and the failed-init
path requests reboot at `0x20001102` then loops at `0x20001106`. Selected GPIO,
UART, SPI, PIO, allocation and flash-program symbols are absent. However SDK
startup at `runtime_init_early_resets` (`0x2000244c`) writes reset masks and
`runtime_init_post_clock_resets` (`0x200024b4`) releases ordinary peripheral
resets, including IO banks/pads. This can change electrical pin state despite
no application GPIO calls. USB initialization (`0x200028a4`) touches USB
controller/DPRAM. The RP2040 GPIO15 enumeration workaround is compiled inert
for this target. Pre-main startup is outside the application watchdog.
Independent linked/startup review remains required before any physical load.

Retained failed builds remain separate: 001 failed on TinyUSB OS-definition and
indentation diagnostics; 002 revealed a replaced Cortex-M33 toolchain flag;
003 linked the ELF but failed export because map generation was missing.
004 uses the SDK's map-only function; no UF2/BIN or loading task is exported.
Installed MCU/FPGA parameters and physical tests remain separate requirements.

Repeat offline checks with `nix develop .#ci --command task forgix:usb-ram:test`.
Build only after committing inputs, using fresh paths and
`nix develop .#forgix-usb-ram --command task forgix:usb-ram:build -- --build .scratch/ram-build-next --output .scratch/ram-artifact-next --jobs 2`.
Software pins and artifact hashes are in `checks.json`; binaries remain private.
