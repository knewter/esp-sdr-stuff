# Forgix production coordinator and checked UID startup

October 4, 2026. The [sanitized checks and actual artifact identities](checks.json)
record offline preparation, not FPGA reception or register proof. The production
coordinator is implemented; its committed registry is empty, so physical loading
remains disabled. OpenSpec FPGA progress remains **1/5**.

The independent backend review identified recovery before loader creation,
incomplete frozen input maps, missing coordinator binding, USB readiness,
initial-persistence clock restart and a legacy preservation entrypoint bypass.
Those findings are fixed. The second review also prompted manifest rechecks
before every hardware stage and qualification rechecks during serial transfers.
The final independent source and actual-artifact review passes at `609613e`, binding all 21 execution inputs and both rebuilt ELFs. Sixteen collector checks and independent delayed-timeout-setter probes also pass. Earlier failures remain private.

The coordinator freezes the exact committed execution map, selects the original
preserved identity, holds the exclusive operator lock and writes durable private
intent/result receipts. A pre-created session lease survives crashes or failed
receipt writes and blocks later device operators until original flash/factory
verification and owned resource closure pass. Initial full preservation itself
changes USB mode, so its failure now also reaches bounded recovery. Unknown
worker/container closure blocks further commands.

Nineteen coordinator checks exercise real Git blobs, exclusive flock, durable
files, failed/changed leases, cancellation, lost acknowledgements, corrupt
journals and deadlines. Twenty-three backend, twenty lifecycle and twenty-three
preservation checks pass. Their injected adapters and regular-file/process
fixtures prove host behavior; they do not prove physical recovery or FPGA registers.

The revised UID helper has no pre-main constructor. Main enables the two-second
watchdog before a read-only ROM chip-info request, checks lookup/return/flags,
rejects zero/erased IDs, and enforces a cooperative 500 ms initialization deadline
before USB. A hanging ROM call relies on the watchdog. Invalid identity causes
normal reboot rather than a fabricated serial. Four actual-C UID fault tests
and nine assembled-PIO regressions pass. SDK reset and other pre-main startup
remain outside that watchdog; this change does not establish whole-ROM timing.

| Rebuilt RAM image | Ordinary SRAM | Embedded FPGA candidate | Physical admission |
| --- | ---: | ---: | --- |
| Configuration003 | 203,700 bytes | 173,380 bytes | Disabled |
| Register-only011 | 28,868 bytes | None | Disabled |

Both actual ELF layout guards and linked startup audits pass. Earlier
configuration002/register010 artifacts remain intact. Source and artifact
hashes are in the receipt; raw ELF/map/disassembly, backups and identities
remain private. GPIO/pad/PIO reset still prevents assuming prior-image continuity;
the selected route configures the exact bound image after RAM startup.

The [prospective register protocol](../../research/forgix-spi-register-trial-protocol.md)
describes admission, preservation, load, configuration, collection and recovery.
It separates the registry from the qualification receipt to avoid a circular
hash dependency, while freezing both at runtime. The 600-second acceptance
clock starts before initial persistence. Existing owned cleanup can add about
42 seconds after an operation timeout; OS responsiveness and actual recovery
need separate qualification. No strict wall-clock recovery claim is made.

The current read-only survey verifies the ESP stable link and both original
4 MiB backups, and finds one RTL-SDR. It finds no factory/ROM Forgix and no USB
device matching its preserved identity. No serial device was opened. The photos
show the nominal 32 MHz oscillator marking; actual frequency/tolerance, FPGA
grade and SPI pad handoff remain unqualified. The oscillator output is wired
only to the FPGA; RP GPIO19 controls enable. USB firmware cannot directly read
that clock through the current wiring.

Next: establish a matching attachment and physical qualification, refresh
preservation, then measure configuration/register readback and several-rate
sequence/CRC transport. USB-only RP results do not complete the FPGA transport
task. No additional ESP wiring is needed for the first internal register test;
later direct ESP-to-Forgix capture requires verified SPI connections and ground.
