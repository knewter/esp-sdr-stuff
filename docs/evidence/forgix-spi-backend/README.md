# Forgix identity-selected backend preparation

Captured October 4, 2026, from source
`d919b8048abf0a2af10eb0ef00994563b83ebf3c`. The
[sanitized receipt](checks.json) records **20 passing backend checks**, actual
RAM builds and their linked startup inspections. This is own-operator offline
preparation. **No device was opened, no FPGA was programmed, and hardware
loading remains disabled.** OpenSpec acceptance stays **1/5**.

The backend connects the previously separate preservation, ROM/RAM load,
configuration, private register collection and factory-return helpers. Its
committed qualification registry is empty. Every hardware method requires an
admitted session; the hidden serial worker also refuses before opening a port.
The public CLI only saves a preparation plan. There is no production coordinator
or hardware run command yet.

## Identity, preservation and resource ownership

Both bridge variants now advertise a 16-digit USB serial descriptor from the
pinned RP2350 SDK unique-ID implementation. The selector requires its normalized
SHA-256 to match the preserved original device, plus the exact USB product,
physical node, tty and enumeration. Tests reject missing/wrong serials and
changed enumerations. The collector worker must match the enumeration used for
configuration; each transfer rechecks identity, the inherited exclusive flock
and frozen execution inputs. This is selector behavior, not measured continuity
between factory, ROM and RAM applications on the attached board.

The adapter binds committed firmware, manifest, ELF, embedded image, original
USB continuity receipt, original full backups and future qualification/review
receipt hashes. Backend and registry sources must be frozen separately; keeping
the registry in its own module avoids a self-referential backend source hash.
The original USB diagnostic's historical image whitelist remains fixed. The
new subclass admits only its exact configuration-profile ELF at a dedicated
private filename through SRAM-only `picotool load -v -x -t elf` arguments.

USB Docker operations stay owned by the existing root container/process
helper. Serial operations use the inherited-lock bounded worker wrapper.
Aggregate closure requires both worker-group and container closure. Unknown
closure prevents further hardware access, including recovery. Device flash is
read twice and compared independently before and after the modeled episode;
RAM load and normal factory return supply no flash-write operation.

## Persistence and failures exercised

Tests compile the actual USB descriptor, configuration and register protocol C
against controlled host adapters. Fragmented configuration replies are bound
to nonce, image and source, journaled and independently reread. Faults exercise
partial receive, disk failure, identity change after open, cancellation, late
cleanup and failed close. Disk persistence failures still reach serial close;
possibly consumed commands are not retried. Journal snapshots remain unchanged
when the returned receipt gains backend fields.

Actual-C register collection retains all 1,664 response bytes, restores the
scratch value and closes once. Failed CRC collection retains its prefix. Other
fixtures verify exact ROM-only load arguments, unchanged legacy whitelist,
two-read preservation translation, changed input rejection and admission
refusal before hardware helpers. These do not establish real FPGA registers.

The adjacent regression suite ran 39 original USB trial checks (38 passed;
its real picotool-version check is skipped in the CI shell), 15 collector,
20 lifecycle/process and 15 configuration checks, all of the latter passing.
Existing local PTY and real process/file fixtures supply host evidence. No
new physical preservation or factory recovery took place in this checkpoint.

## Rebuilt images and startup limits

| Image | Ordinary SRAM | Embedded candidate | Admission |
| --- | ---: | ---: | --- |
| Configuration bridge002 | 203,152 bytes | 173,380 bytes | Disabled |
| Register-only bridge010 | 28,440 bytes | None | Disabled |

Both builds pass their respective 256 KiB and 128 KiB layout guards, and the
backend verifies the configuration manifest, current committed inputs and
linked image bytes. Both linked reset audits still show GPIO/pad/PIO reset
before `main`. Earlier bridge009/config001 receipts remain unchanged.

Saved ELF/map/disassembly inspection binds the sole `.init_array` entry to
`_retrieve_unique_id_on_boot`. Its linked RP2350 implementation looks up ROM
`GET_SYS_INFO` and requests chip information, then caches the ID. The source's
return-code assertion is compiled out in Release. This pre-main ROM query is
**outside the main watchdog**; the audit is not a whole-ROM/control-flow or
recovery proof. It contains no flash/OTP write. USB descriptor tests use a
synthetic ID, not the attached device's ID.

## Commands and next gate

```sh
nix develop .#ci --command task forgix:spi-bridge:backend:test
nix develop .#ci --command task forgix:spi-bridge:backend:plan -- \
  --plan .scratch/forgix-spi-backend-plan-001
nix develop .#forgix-spi-bridge --command task forgix:spi-bridge:build -- \
  --build .scratch/forgix-spi-config-build-002 \
  --output .scratch/forgix-spi-config-artifact-002 \
  --candidate .scratch/forgix-fpga-candidate-003
nix develop .#forgix-spi-bridge --command task forgix:spi-bridge:build -- \
  --build .scratch/forgix-spi-bridge-build-010 \
  --output .scratch/forgix-spi-bridge-artifact-010
```

Fresh directory names are required for repeats. No programming command is
provided. Qualify the actual FPGA grade, clock and pin handoff, independently
review the entire configuration/load/recovery path (including pre-main ROM
identity), and implement production coordinator admission before registering
any artifact. Then fresh full preservation, physical UID continuity and
register readback precede the several-rate sequence/CRC transport benchmark.
Tasks 1.1 and 2.1–2.3 and the accepted ledger remain unchanged.

Source: [backend](../../../tools/forgix_spi_backend.py),
[qualification registry](../../../tools/forgix_spi_qualifications.py),
[tests](../../../tests/test_forgix_spi_backend.py),
[USB descriptor](../../../firmware/forgix-spi-bridge/usb_descriptors.c).
Prior evidence: [configuration](../forgix-spi-config/README.md),
[collector](../forgix-spi-collector/README.md),
[lifecycle](../forgix-spi-lifecycle/README.md),
[startup](../forgix-spi-bridge/README.md).
