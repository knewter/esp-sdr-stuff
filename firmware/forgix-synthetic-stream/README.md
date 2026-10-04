# Offline synthetic stream RAM profile

This separate profile is not admitted for loading. The finite engine and wire
schema are in [PROTOCOL.md](PROTOCOL.md). Host tests exercise the actual C
engine with injected bounded callbacks; they do not establish electrical
turnaround, FPGA timing, USB throughput, or recovery.

The adapter stages the committed configuration, checked ROM UID, descriptors,
and PIO source from `firmware/forgix-spi-bridge/`. It extracts the reviewed PIO
function bodies from that profile's `main.c` unchanged. An explicit request
encoder replaces only its register whitelist with the synthetic source map
at `0x10000`; the original profile and whitelist remain separate. The adapter
does not add SPI retries. Each transaction retains the existing CS/high-Z
cleanup and acknowledgement parser; the engine requires POP readback because
SPIBone acknowledgement cannot distinguish a rejected write.

Watchdog enable precedes checked UID initialization, USB initialization and
application GPIO. The 30-second command and 120-second lifetime clocks include
this initialization time. Direct TinyUSB has one owner, no stdio interface,
and distinct product ID `0x4013`. The application uses no heap or core1 and
requests a 4 KiB stack. The ring holds exactly sixteen immutable 512-byte
frames. Final ARM ELF inspection, SDK startup/pin-state disassembly and the
actual compiled object/image memory ranges remain required before admission.

The new image parser requires a successful, closed compiler candidate and
replays its complete committed source, generated project, CSR, stage, pin and
fresh-image guards. It accepts canonical byte-per-line hex, at most 192 KiB
decoded. The builder embeds those exact bytes and CRC/SHA, records all staged
source hashes, and rechecks them after building. Its named ELF policy permits
only ordinary no-flash SRAM, at most 256 KiB total allocation including image,
engine and stack; original USB and bridge policies retain their own gates.

After committing all inputs and obtaining independent source review, an
operator can run this build-only command with a fresh private Task recipe:

```sh
nix develop .#forgix-spi-bridge --command python tools/build_forgix_synthetic_stream.py \
  --candidate .scratch/forgix-synthetic-candidate-003 \
  --build .scratch/forgix-synthetic-stream-build-001 \
  --output .scratch/forgix-synthetic-stream-artifact-001
```

Candidate paths must belong to the same repository context as the verified
compiler output. There is no relocation fallback or stale output acceptance.
The separate `--rp-pause` variant binds its fixed 100 ms RP pause into the
build identity; it is not a host-reading pause. No builder command configures
an FPGA, accesses USB or admits the resulting ELF for loading.
