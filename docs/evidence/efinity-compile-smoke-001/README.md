# Efinity compiler trial 001: missing interface stage

On 2026-10-02 the root operator ran the reviewed, fixed generic Trion
**T8F81/C2** vendor fixture through the Nix FHS runtime:

```sh
nix develop .#forgix --command task forgix:efinity:compile-smoke -- --private .scratch/efinity-compile-smoke-001
```

The vendor runner exited **0** and reported synthesis (`map`), placement/routing
(`pnr`) and bitstream-generator (`pgm`) completion. Its Interface Designer import
failed because its bundled Python could not load `libsqlite3.so.0` in the Nix
runtime, so the runner skipped that stage. The bitstream generator subsequently
reported that its required interface constraint file was missing and produced
**no hex image**. The project validator refused this incomplete result, retained
the failed private output, and verified closure of its owned process group.
The compiler episode lasted approximately **12.74 seconds**.

This is a failed full-compiler check despite the vendor exit code. The four-stage
and fresh-bitstream requirements remain intact. No attached hardware was opened,
no Forgix bitstream was produced and no firmware was replaced. Compiler licensing
is not accepted from this result. The bundled C++ library compatibility warning
was retained; its library was not removed or replaced.

[Machine-readable sanitized result](results.json) records source and fixture
hashes. [Independent preflight](../efinity-compiler-independent-review/README.md)
proved the helper guards using synthetic cases; this actual run demonstrates why
stage and fresh-image checks are necessary. Proprietary fixture files, generated
outputs and raw vendor logs remain in ignored private storage.
