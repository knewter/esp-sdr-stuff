# Exact-image RAM configuration bridge: offline build

October 3, 2026 (local). **The configuration variant compiles, its linked
image matches the decoded candidate, and 15 focused checks pass. No hardware
was opened, RAM loaded or FPGA programmed.** These are own-operator host
checks, not an independent load/recovery review or physical qualification.
The [receipt](checks.json) binds committed code, artifacts and private logs.

The opt-in configuration bridge uses **202,680 bytes of ordinary SRAM**,
including the **173,380-byte decoded image**. Its ELF is 814,292 bytes with
debug/metadata; that file size is not its SRAM allocation. Register-only
bridge009 still uses 27,968 SRAM bytes. Both compiled artifacts pass the pinned
SDK startup audit, which still shows GPIO/pad/PIO resets before main.

## Configuration after startup

The [new C writer](../../../firmware/forgix-spi-bridge/config.c) performs an
exact embedded-image configuration after SDK startup, before register ARM.
`FGSC` is a separate fixed 48-byte request with a nonzero nonce, SHA-256 of
the decoded bytes and CRC. It cannot replace image contents or choose arbitrary
pins. The matching 128-byte reply binds nonce, image, compiled source identity,
status and CRC. A configuration attempt is consumed before GPIO work; replay,
configuration after ARM and admission at/after 30 seconds are refused.
The main loop caps configuration at 20 seconds and at the boot-window end.

The [pinned factory loader](https://bitbucket.org/adiuvo-engineering/forgix_public/src/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/BitStream_Loader/firmware/pico/src/fpga_config.c),
[board constants](https://bitbucket.org/adiuvo-engineering/forgix_public/src/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/BitStream_Loader/firmware/pico/include/board_config.h)
and [host decoder](https://bitbucket.org/adiuvo-engineering/forgix_public/src/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/BitStream_Loader/host/forge_loader/bitstream.py)
ground mode-3 MSB-first transmission, reset/oscillator waits, trailing clocks
and full hex decoding. The implementation retains the entire decoded prefix;
it does not strip a guessed header. It checks image CRC and MCU clock before
GPIO work, requires CDONE low during reset, sends all bytes plus 32 zero bytes,
then requires CDONE high. CS rises before DATA release on success and failure.

Software clock edges request 1 microsecond phases and check absolute deadlines
per bit. Watchdog and USB service continue during image transmission. Fake
SDK tests exercise deadline crossings during reset, transmission, USB service
and final cleanup. They also check exact MSB byte order and release ordering.
They do not measure pad timing, frequency, contention or metastability.
CDONE is a configuration indication, not physical image identity or continuity.

## Guard and host boundaries

The [builder](../../../tools/build_forgix_spi_bridge.py) requires a successful,
matching private T8F49/I2 candidate receipt. It binds both hex and decoded-byte
hashes into the source identity, freezes inputs during compilation, and checks
the exact image in the ELF's loadable segment. The image cap is 192 KiB.
A distinct `spi-config-bridge` profile caps SRAM allocation at 256 KiB and
requires configuration/image symbols. Existing USB and register-only profiles
remain capped at 128 KiB. All reject non-SRAM destinations, flash writers,
heap/core1 allocation and a different core0 stack size.

The [host helper](../../../tools/forgix_config.py) uses injected caller-owned
transport, persists intent before transmission and retains partial response
prefixes. It refuses wrong identity/framing, invalid progress and late or
unpersisted completion. It opens no port and provides no programming CLI.
Private caller-owned journal/lock/enumeration/closure and factory recovery
remain the physical backend's responsibility.

```sh
nix develop .#ci --command task forgix:spi-bridge:config:test
nix develop .#forgix-spi-bridge --command task forgix:spi-bridge:build -- \
  --build .scratch/forgix-spi-config-build-001 \
  --output .scratch/forgix-spi-config-artifact-001 \
  --candidate .scratch/forgix-fpga-candidate-003
nix develop .#forgix-spi-bridge --command task forgix:spi-bridge:startup-audit -- \
  --artifact .scratch/forgix-spi-config-artifact-001 \
  --output .scratch/forgix-spi-config-startup-001
```

Use fresh ignored paths for another run. The candidate's I2 grade and 32 MHz
clock remain provisional. This removes a missing firmware mechanism; it does
not establish a reviewed physical loading path. Next: qualify grade/clock and
pin timing, implement/review the identity-selected backend, refresh full
preservation, then obtain actual configuration and register readback evidence.
The [lifecycle preparation](../forgix-spi-lifecycle/README.md) remains a model;
OpenSpec physical acceptance stays **1/5**, with no new checked task.
