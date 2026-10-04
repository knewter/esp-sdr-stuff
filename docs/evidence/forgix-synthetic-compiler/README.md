# Separate synthetic FPGA compilation route

October 4, 2026. The compiler helper has passed 13 author and 13 independent
source-review groups, including complete actual LiteX generation with vendor
subprocesses mocked, exact four-pad and two-HDL-input checks, committed input
binding and bounded owned-process cleanup. The reviewed empty-clock-constraint
failure was corrected by retaining the pinned board finalizer.

The first actual FHS attempt failed before generation or compilation: Git was
absent inside the Efinity environment, so committed-input verification raised
FileNotFoundError. Only private console and failed receipt were produced;
parent-attested group closure and output hardening pass. [Checks](checks.json)
retain the executed commit, hashes and failure without publishing vendor output.
Git is now explicitly declared in both the Nix FHS and Forgix shell. Runtime
verification and a fresh compile must demonstrate the correction.

Repeat the read-only boundary check with
`nix develop .#forgix --command task forgix:synthetic:candidate:runtime`.
Then compile with `nix develop .#forgix --command task forgix:synthetic:candidate:compile -- --private .scratch/FRESH_BUILD`.

The requested target is provisional T8F49/I2 with a nominal 32 MHz clock.
No resource fit, timing closure, programming admission or physical stream is
claimed. Actual reports, pins, image and warnings still need independent review;
board parameters and the entire load/recovery path remain separate gates.
