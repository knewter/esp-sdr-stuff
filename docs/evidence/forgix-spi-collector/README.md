# Private FPGA register collector: host checks

October 3, 2026 (local). **Fifteen host checks pass, with no skips. No hardware
port was opened, FPGA programmed or RAM bridge loaded.** The sysfs-only survey
separately finds the factory Forgix, CP2102 bridge and RTL-SDR Blog V4 present;
enumeration does not verify their application state or refresh preservation.

The [receipt](checks.json) binds source commit
`f2b5db2b549e5296509756f42f2588d05837cd29`, execution-file hashes, test duration
and private log hash. Tests use fragmented replies from the real compiled C
protocol, a fake register bank/clock, injected failures and a local pseudo-terminal.
This is own-operator host evidence, not independent review or physical transport
qualification.

```sh
nix develop .#ci --command task forgix:spi-bridge:collector:test
```

## What is implemented

The [collector](../../../tools/forgix_spi_capture.py) wraps the existing finite
register engine. Its lifecycle caller supplies an already-selected transport
factory, identity check and exclusive-lock check. The included sysfs selector
requires the distinct `cafe:4012` bridge product, explicit physical USB socket
and matching tty ancestry. RAM firmware has no serial string: this selector
does not replace factory/ROM identity continuity or identify the FPGA image.
The inherited-flock helper inspects the caller's lock without acquiring,
unlocking or closing it.

Before I/O, the collector creates private 0700/0600 output under the caller's
ignored backups area. It syncs directory entries, journals each transfer intent
before calling the transport, and flushes/fsyncs received bytes before returning
them to the register validator. A write intent is not proof of device consumption.
Every returned byte, including a late or invalid prefix, is retained without
resynchronization. Transcript, raw replies and journal remain private; the
manifest omits raw exception messages.

After a run, it closes its owned transport and independently rereads the saved
raw/journal files against the returned bytes/events. Disk loss, failed closure
or exceeding the 30-second cooperative deadline prevents success. Ambiguous
I/O stops further commands; a valid pattern mismatch still permits the existing
engine's scratch restore/readback and FINISH. Cancellation retains the failed
prefix/manifest and propagates. Persistence failure can itself prevent a final
manifest write; the future owning worker must retain that failure too.

The [tests](../../../tests/test_forgix_spi_capture.py) exercise successful
fragmented exchanges, original-scratch restoration, pattern mismatch, corrupt
CRC, late reply, partial cancellation, lock/enumeration changes, failed journal
commit, partial raw write, truncated saved raw, intent persistence crossing a
deadline, failed/late closure, invalid source/nonce and strict USB ancestry.
The real POSIX serial adapter is checked on a local PTY, including deadline
expiry and actual descriptor closure.

## Remaining lifecycle boundary

There is **no physical collector CLI or load/program task**. OS/USB operations
still need a bounded owning worker, frozen inputs, failed-open closure and the
full reviewed preservation/configuration/RAM-load/factory-recovery path. The
collector always reports `factory_return_verified=false` and
`lifecycle_complete=false`; register verification and FINISH are insufficient.

The [startup audit and bridge artifact](../forgix-spi-bridge/README.md) remain
unchanged. FPGA grade, physical clock, pin timing and image continuity across
SDK startup resets remain unqualified. The next implementation must resolve
that configuration transition before admitting a physical register trial.
OpenSpec remains **1/5 tasks complete**.

The publication now bounds generated pages/assets separately at 2 MiB and the
whole site at 24 MiB, keeping the 120-second build budget. The previous 16 MiB
total was nearly full, chiefly from immutable historical sources. All prior
evidence and exported source bytes remain available.
