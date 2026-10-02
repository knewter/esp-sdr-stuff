# Actual complete Efinity compiler test

On 2026-10-02 Efinity **2026.1.132** completed the fixed bundled generic
**Trion T8F81/C2** project through the locked Nix FHS environment:

```sh
nix develop .#forgix --command task forgix:efinity:compile-smoke -- --private .scratch/efinity-compile-smoke-002
```

| Required result | Actual evidence |
| --- | --- |
| Synthesis (`map`) | PASS and matching stage completion |
| Interface Designer (`interface`) | PASS and matching stage completion |
| Placement/routing (`pnr`) | PASS and matching stage completion |
| Bitstream generation (`pgm`) | PASS and matching stage completion |
| New hex image | 520,140 bytes; created after this run started |
| Vendor exit | 0 |
| Owned process group and private files | Closure and 0700/0600 protections verified |

The complete compiler episode lasted **23.73 seconds**. The new hex SHA-256 is
`0966d77c7aee2847354814d4e7d80292fc026b5cce237decbea5b81042ef0787`.
Only the four pinned project inputs were copied into a fresh ignored directory;
no shipped cached output was reused. The flow is `compile`, with a 300-second
vendor deadline and a 330-second outer supervisor. Optional binary conversion
was not requested. No programmer stage or attached hardware was used.

The [initial actual run](../efinity-compile-smoke-001/README.md) remains failed:
Interface Designer could not import SQLite, and the runner misleadingly exited
success without generating a hex file. Import-only probes then exposed a second
missing D-Bus library. Adding the pinned Nix SQLite and D-Bus packages made the
complete import succeed. Neither package starts a service in this environment.
The fixture, compiler command and four-stage/fresh-image acceptance were unchanged.
The bundled C++ library compatibility warning remains visible privately; the
vendor library was not removed or replaced. **51 focused helper tests pass**.

[Sanitized receipt](results.json) binds the actual source, helper, runtime and
fixture hashes. [Independent actual-result review](../efinity-compiler-independent-review/actual-002-review.md)
retains preflight guards and actual-result replay. Vendor inputs, raw logs and
generated bitstreams remain ignored and private.

This verifies that the installed compiler can build this generic vendor example
under the present licensing configuration. It does not identify a license file,
validate every FPGA family, or prove the connected Forgix's physical constraints.
The fixture uses **T8F81/C2**, while the Forgix is expected to use T8F49; its fitted
grade, oscillator, board revision and pin layout still need physical confirmation.
No Forgix MCU/FPGA firmware or ESP32 firmware changed, and no transport benchmark
ran. [Setup and repeat commands](../../research/forgix-toolchain.md) distinguish
this software check from the guarded connected-board build.
