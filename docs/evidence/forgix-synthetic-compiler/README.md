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
Git is now explicitly declared in both the Nix FHS and Forgix shell. The corrected actual FHS boundary passes independent review: all 11 committed
input hashes match. The first failed output is retained.

Repeat the read-only boundary check with
`nix develop .#forgix --command task forgix:synthetic:candidate:runtime`.
Then compile with `nix develop .#forgix --command task forgix:synthetic:candidate:compile -- --private .scratch/FRESH_BUILD`.

The requested target is provisional T8F49/I2 with a nominal 32 MHz clock.
No resource fit, timing closure, programming admission or physical stream is
claimed. Actual reports, pins, image and warnings still need independent review;
board parameters and the entire load/recovery path remain separate gates.

## Second actual attempt

All four vendor stages report PASS and a fresh image exists. The worker still
refuses success because the vendor changed the generated project XML hash;
all eleven committed inputs and the other seven generated files remain exact.
The failed receipt and reports stay private. A precise reviewed before/after
XML contract is needed; removing the input guard would not resolve the issue.

The actual internal timing report also shows setup slack −0.694 ns against the
requested 31.25 ns period. This does not close 32 MHz timing, regardless of
compiler stage status. Full independent report review and critical-path diagnosis
are in progress. No image was loaded and no physical FPGA claim follows.
