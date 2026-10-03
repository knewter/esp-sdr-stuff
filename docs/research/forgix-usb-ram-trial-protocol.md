# Prospective Forgix RAM USB trial, condition 001

Declared before hardware on October 2, 2026. This evaluates synthetic
RP2350-to-host USB payload only. The user reports USB-only wiring and can
unplug/replug. FPGA markings remain unknown. No FPGA configuration transaction,
ESP operation or RTL receiver operation belongs to this episode.

One run requests **65,536 payload bytes/s for 60 seconds**, with exactly one
host read pause requested at 30 seconds for 100 ms. Record actual pause timing.
Do not retry or sweep rates automatically. Proposed 256 and 768 KiB/s conditions
require separate reviewed episodes. Each record is 512 bytes with 460 payload
bytes; account for framing separately from payload.

Freeze the committed lifecycle, collector, firmware sources, this protocol,
ELF and map hashes, compiled source identity, SDK/TinyUSB closure, picotool
executable and immutable scoped USB image before device access. A historical
artifact is allowed only with its exact committed source set independently
verified; the current merged Taskfile must not be substituted in that identity.
[Offline build](../evidence/forgix-usb-ram-build/README.md) is preparation only.

Root is the sole operator. Acquire the shared exclusive operator lock and
select factory USB by exact physical topology plus its existing unique identity
hash. Select each tty through its sysfs USB ancestry; no guessed ACM number.
Require factory HELLO/STATUS ready/idle, matching private full 2 MiB backups
and fresh ROM verification against the device before loading. Software ROM
entry and every subsequent USB operation must target that same identity.

The ELF guard must pass all ordinary-SRAM load ranges, vectors, metadata,
stack/heap bounds and reviewed linked startup. Use only explicit ELF
`picotool load -v -x` with freshly selected bus/address. SDK startup resets IO
banks/pads; no application GPIO calls do not imply unchanged electrical state.
The firmware's pre-main code is outside its watchdog. A startup hang requires
physical replug rather than an invented software-recovery guarantee.

The transient RAM device has VID/PID `cafe:4011` and product
`Forgix USB RAM diagnostic v1`, with no serial descriptor. Its identity chain
is factory identity → selected ROM load → same physical USB port → exact
compiled CONFIG hash/profile → fresh private nonce. Open serial exclusively,
start the reader, validate CONFIG and then send START. Verify every record's
CRC, length, deterministic payload, nonce, sequence and device timestamp.
Preserve raw received bytes, including invalid or late prefixes, privately;
never silently resynchronize or omit failed records.

The collector has an absolute 85-second bound including startup and END grace.
The firmware permits one run, a fixed two-second drain and a 120-second maximum
main lifetime; a two-second watchdog stops hangs after initialization. Record
host payload/time, inter-arrival distribution, actual pause, device generation,
queue/drop counters, partial writes, backlog high-water and stalls. CDC accepted
bytes do not prove host delivery. Reconcile END snapshot counters and sequence
gaps; unexplained gaps, invalid data, missing END or missed deadlines fail the
trial. A fully accounted queue overflow is retained as measured loss, not a
zero-loss success.

After every outcome close all serial/libusb handles and confirm closure of
owned processes, groups and uniquely scoped containers. Wait for the factory
identity; obtain physical replug if necessary. Verify the original full saved
flash against the device through fresh targeted ROM entry, return to factory
and repeat HELLO/STATUS ready/idle. An unchanged backup file alone cannot prove
unchanged device flash. Failure to verify return or flash leaves recovery
unverified and prohibits another automatic hardware episode.

Publish sanitized numeric receipts and an independent review. Success narrows
the USB segment budget; it establishes neither FPGA-to-RP transport, FPGA SRAM
access, ESP DMA reachability nor RF continuity. All original FPGA and RF
acceptance gates remain unchanged.

## Separately declared condition 002

Declared before loading after the user-directed reconnect and successful
[factory stability and recovery 003](../evidence/forgix-usb-ram-recovery/README.md).
The failed pre-load episode 001 and failed recoveries 001/002 remain retained.
This permits one new attempt at the same 65,536 payload bytes/s, 60-second
condition and requested 100 ms host read pause, using the exact reviewed
historical build004. The lifecycle's bounded factory/diagnostic access waits
and late-result rejection have passed independent review at `e315d6b`.
Freeze this amended protocol and the current committed execution inputs,
repeat all runtime/artifact and fresh full-flash gates, then load once.
Use a new private episode directory. All capture, closure, full post-trial
flash/factory verification and failure retention rules above still apply.
No automatic retry or rate sweep is permitted.
