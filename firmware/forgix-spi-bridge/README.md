# Finite Forgix RP PIO register bridge

This is an offline RAM-only candidate, not a verified FPGA transport. The
default register-only variant has no FPGA configuration loader and requires
the exact qualified guarded image already present. An opt-in
[exact-image configuration variant](../../docs/evidence/forgix-spi-config/README.md)
now compiles and can configure its embedded candidate after SDK startup,
before ARM. Neither variant has a flash/OTP writer, RF input, PSRAM access or
sustained streaming path. Both require a separately reviewed hardware lifecycle.
No load/program task is provided. Physical grade/clock, PIO handoff timing,
linked startup, exclusive USB identity, fresh preservation and factory recovery
remain prerequisites. Compilation and digital simulation do not satisfy them.

The fixed register ABI is taken from guarded candidate003's generated CSR map:
counter read at `0x1000`; scratch read/write at `0x1004`. Reset, controller,
identifier and every other address are refused. SPIBone serializes command,
address and data in big endian; writes use command0, reads command1. Its ACK/ERR
wire response is indistinguishable, so actual scratch readback is required to
verify a write. A successful response alone is not write verification.

## Build and check

Commit sources before building. All tools, SDK2.2.0, its exact TinyUSB submodule,
ARM compiler, native test compiler and pioasm2.2.0 come from the locked flake.
Build and plan outputs require fresh private paths under ignored `.scratch/`.

```sh
nix develop .#forgix-spi-bridge --command task forgix:spi-bridge:test
nix develop .#forgix-spi-bridge --command task forgix:spi-bridge:build -- \
  --build .scratch/forgix-spi-bridge-build-001 \
  --output .scratch/forgix-spi-bridge-artifact-001
nix develop .#forgix-spi-bridge --command task forgix:spi-bridge:plan -- \
  --plan .scratch/forgix-spi-bridge-plan-001
```

The build binds committed source bytes, SDK and compiler provenance, generated
PIO words, ELF/map/disassembly and a distinct application layout policy. The
original synthetic USB diagnostic still uses its stricter no-application-GPIO
policy. Both reject flash/peripheral ELF destinations, heap/core1 allocations,
flash-writing symbols and allocations beyond128KiB. These are layout checks,
not an instruction-level safety proof. The separate configuration profile has
a 256 KiB allocation limit, a 192 KiB image cap and required image/writer symbols;
the default profiles retain their 128 KiB limits. The SDK resets IO before main; a RAM
image cannot promise that the previous FPGA configuration or pin state survives.

## Requested pin and timing contract

For the register-only variant, application GPIO work begins only after a valid ARM request within30seconds:
GPIO1 CS high, GPIO2 SCK low, GPIO3 DATA input, GPIO5 CDONE input,
GPIO19 oscillator enable high. GPIO4 CRESET is untouched by application code.
The bridge requires the SDK's150MHz MCU clock, waits100us, and refuses unless
CDONE is high. CDONE proves a configuration indication, not the loaded image's
identity. A separate lifecycle must bind the exact previously loaded bitstream.

PIO0 owns only GPIO2/3. CS remains software-controlled and high through setup.
The requested divider4.6875 yields a nominal32MHz PIO instruction clock; its
fractional divider and physical pad latency remain unmeasured. Each request
bit takes33PIO cycles, with long low/high phases. All request words are queued
before CS assertion. The final request rise is followed by17PIO cycles before
`SET PINDIRS,0`, then80additional high-clock cycles before a completion IRQ.
No CPU instruction or host response is required to release DATA. A delayed CPU
leaves SCK high and DATA input at this completed handoff. Fresh20ms software
deadline checks precede handoff and result acceptance, even when flags/FIFOs
are already ready. The deadline is capped by the120second lifetime. These
polling checks are not a CPU-stall-independent hard real-time pin-abort proof;
the2second watchdog is the separate fallback for a stopped CPU.

Receive initialization's low side-set supplies the falling handoff only
after that guard. DATA stays input throughout64response bytes, including
pending0xff bytes and the response header/payload. A fixed20ms deadline bounds
both PIO waits and FIFO drains. Ending/aborting raises raw CS first, stops PIO,
leaves DATA input, sets SCK low and waits100us before any later reacquisition.
An already issued FPGA write cannot be rolled back by an abort. Oscillator
enable stays high until reboot. No claim of electrical contention safety or
actual32MHz FPGA operation follows from these requested settings.

The PIO instruction-subset interpreter drives the real GuardedSPIBone Migen
model across clock phases. It tests the assembled words and fixed nominal
clocks; it does not implement a complete RP simulator, input synchronizer,
MMIO latency, FIFO-full stalling, fractional-divider jitter or metastability.
Linked artifact review and physical qualification still precede loading.

## USB protocol v1

Distinct CDC device `cafe:4012`, product Forgix SPI RAM bridge v1, no serial
string. One main-loop TinyUSB owner; UART/USB stdio, heap and core1 disabled.
A2second watchdog starts before USB initialization in main; startup before
main is outside it. Independent120second lifetime requests normal flash
reboot. FINISH admits no later commands and drains for1second before reboot.
There is one ARM attempt and at most24sequential commands in that session.

Requests are48bytes: `FGSB`, version1 byte, opcode byte
(1ARM/2READ/3WRITE/4FINISH), two zero bytes, sequence uint32LE, nonce16,
address uint32LE, value uint32LE, eight zero bytes, CRC32IEEE over44bytes.
ARM requires sequence1, nonzero nonce, zero address/value and the startup
window. Later requests require the exact nonce and next sequence. CRC,
reserved fields, replay or nonce/order failures are inert. A session-bound
unsupported command consumes its sequence and returns refusal without SPI.
Reads require zero value; ARM/FINISH require zero address/value.

Replies are128bytes: same magic/version/op, status byte, zero byte, sequence,
nonce16, address, result uint32LE, timestamp uint64LE, committed source-set
SHA256ASCII64, requested PIO/FPGA clock32000000 uint32LE, MCU clock150000000
uint32LE, eight zero bytes, CRC32IEEE over124bytes. Status0 is a response
accepted by the bridge,1refusal,2timeout,3invalid/truncated SPI response,
4CDONE low,5MCU clock mismatch. The host refuses unexpected identity,
sequence, nonce, register, clock profile, reserved fields, CRC or error status.

The offline plan saves original scratch, reads the counter, verifies three
scratch patterns including a final zero bit, then reads the counter again.
The physical collector must verify counter progression and every
scratch value, restore the original scratch, read it back, then FINISH and
independently verify complete original flash/factory return. It must retain
failed or partial runs. The injected-transport `RegisterRun` engine now implements that register test
and retains partial exchanges in memory. The new private collector persists
transfer intents and raw reply prefixes, checks the caller's lock/enumeration,
and verifies serial closure. Fifteen own-operator C/PTY/fault checks pass; see
[collector evidence](../../docs/evidence/forgix-spi-collector/README.md).
The [offline lifecycle controller and worker wrapper](../../docs/evidence/forgix-spi-lifecycle/README.md)
now pass ordering/closure tests. Its physical caller still needs complete
image binding, reviewed load/configuration/recovery and full factory return. Ambiguous replies
stop further commands; valid pattern mismatch still attempts restoration.
FINISH acknowledgment is not factory return. No physical trial CLI or complete
load lifecycle is provided. The saved-ELF startup audit runs separately:

```sh
nix develop .#forgix-spi-bridge --command task forgix:spi-bridge:startup-audit -- \
  --artifact .scratch/forgix-spi-bridge-artifact-008 \
  --output .scratch/forgix-startup-audit-001
```

The narrow recognized-sequence audit binds linked reset code/initializer slots
and SDK reset defaults; it does not prove electrical/configuration continuity.

Primary implementation references: [pinned SPIBone](https://github.com/enjoy-digital/litex/blob/8c01073afb71aa0a0709f02f8e24247589e8f5e4/litex/soc/cores/spi/spi_bone.py),
[Raspberry Pi PIO APIs](https://www.raspberrypi.com/documentation/pico-sdk/hardware.html#hardware_pio)
and the committed FPGA guard's explicit RP contract in `tools/forgix_spi_guard.py`.
