# Bounded synthetic RP2350 USB RAM build

Offline build/preflight only. This is an MCU-to-host synthetic diagnostic, not
FPGA transport, PSRAM access, hidden SDR, device readiness or recovery proof.
It changes no physical acceptance gates and has no load/program task.

Use the locked `forgix-usb-ram` shell and `task forgix:usb-ram:build` after
committing scoped source. Pico SDK2.2.0 and its exact TinyUSB submodule are
assembled by Nix; CMake fetches nothing. The SDK `pico2` MCU/12MHz clock profile
is a requested MCU build setting, not a verified Forgix revision or FPGA clock.

One main-loop TinyUSB device owner; SDK UART and USB stdio are disabled. No
application GPIO, LED, SPI, PIO, PSRAM, FPGA configuration or flash/OTP APIs.
The SDK startup still resets ordinary peripherals, including IO banks/pads,
and releases peripheral resets after clock initialization. Therefore zero
application GPIO calls cannot prove unchanged previous electrical pin states.
The actual linked map/disassembly require independent review before any load.

A watchdog starts in main before USB initialization (2 seconds, fed only before
an independent120-second deadline). Startup before main is outside this watchdog.
The application requests normal flash reboot on expiry; that remains untested.
One START within30 seconds permits one60-second producer run and at most2 seconds
of drain. Later commands never restart it. No host presence means finite reboot.
No physical reset route or replacement-image recovery is proved by compilation.

## Binary protocol v1

CDC descriptor has a distinct product and no serial-number string. No printf,
command echo, device addresses or foreign input bytes are output. A valid32-byte
START is: `FRAM`, uint16LE version1, uint16LE command1, uint32LE requested payload
rate (65,536,262,144 or786,432 B/s),16-byte per-run nonce, CRC32IEEE over28 bytes.
Invalid input is silent/inert. Host reader must precede START.

All output records are512 bytes: magic4, version uint16LE, type uint16LE
(0CONFIG/1READY/2DATA/3STATS/4END), sequence uint32LE, total length uint32LE,
payload length uint32LE460, device timestamp uint64LE, nonce16, flags uint32LE0,
payload460, then CRC32IEEE over the first508 bytes. CONFIG uses zero nonce;
other records use the accepted nonce. DATA byte i is
`((sequence*131+i*17)^nonce[i%16])&255`; no RF payload is involved.

STATS/CONFIG/READY/END payload offsets:0 rate u32;4 generated records u32;
8 enqueued records u32;12 discarded records u32;16 partial-write calls u32;
20 queue high-water u32;24 CDC-accepted bytes u64;32 stalled-loop duration us u64;
40 boot time us u64;48 START time us u64;56 maximum lifetime us u64;
64 committed source-set SHA256ASCII;128 distinct profile string.
Counters in these records are snapshots before enqueueing that record itself.
Sequence increases for every generated record, including discarded records;
the bounded16-record queue and CDC buffers can overflow during a host pause.
CDC-accepted bytes/tx callbacks are stack observations, not host-delivered counts.
Host sequence/payload/CRC and timing verification is required independently.
No damaged prefixes may be silently dropped by a future host collector.

ELF guard rejects flash/OTP/peripheral destinations, aliases, overlap, out-of-range
BSS/stack, non-ARM/non-RP2350 metadata, missing RAM vector metadata or >128KiB
summed LOAD allocations. Ordinary main and scratch SRAM are allowed; address
gaps are not counted as allocation. Explicit4KiB core0 stack, no core1 stack or
heap reservation, no linked allocation/programming/application GPIO symbols.
This guard is layout/metadata inspection, not a proof of every linked instruction.
A fresh build exports ELF,map,symbols,disassembly and a hash-bound private manifest.
Future hardware needs source/linked-startup review, identity/preservation, an
exclusive operator and an independently verified recovery lifecycle.
