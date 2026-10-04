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
Actual reports establish resource fit for the requested provisional target.
Timing closure, programming admission and a physical stream remain unproved;
board parameters and the entire load/recovery path remain separate gates.

## Second actual attempt

All four vendor stages report PASS and a fresh image exists. The worker still
refuses success because the vendor changed the generated project XML hash;
all eleven committed inputs and the other seven generated files remain exact.
The failed receipt and reports stay private. A precise reviewed before/after
XML contract is needed; removing the input guard would not resolve the issue.

The actual internal timing report also shows setup slack −0.694 ns against the
requested 31.25 ns period. This does not close 32 MHz timing, regardless of
compiler stage status. Independent report review verifies 3,652/7,384 logic elements, 8/24 RAM blocks,
exactly four assigned user pads and the failed timing result. The worst path
starts at stop_tick and reaches FIFO high-water control through drain expiry.
A source optimization must retain the exact five-second drain semantics. No image was loaded and no physical FPGA claim follows.

The [corrected XML contract](../../research/forgix-project-xml-mutation.md)
passes 20 focused checks and independent rewrite/tamper/file probes. It accepts
only unchanged project bytes or the exact pinned vendor rewrite, retains original
bytes and both hashes, and keeps the other seven generated inputs exact. Empty
auxiliary reports are bounded and hash-retained; critical files stay nonempty.
Actual attempt002 remains failed. Fresh compilation and routed timing are next.

## Third actual attempt

A fresh build at 9ebac50 passes all four vendor stages and complete input,
generated-file, exact XML-rewrite and image verification. Independent review
recomputes all eleven committed inputs, eight generated bindings and 47 retained
outflow hashes. The 520,140-byte hex image is bound in [checks](checks.json).
No FPGA was programmed.

The routed result still fails internal 32 MHz setup: −1.763 ns, with +0.641 ns
hold slack. The deadline-register change preserves behavior but did not improve
this routed result. Resources fit: 3,630/7,384 logic elements and 8/24 RAM blocks.
The four assigned pads are unchanged. External SPI input/output delays and
physical turnaround remain unqualified.

The new worst path runs from tick[5] to stop_tick[41]'s clock enable through
64-bit tick-minus-start scheduling and finite completion, with 55 logic levels.
The next source change will replace that scheduling cone with a bounded
countdown, prove exact record ticks and concurrent control behavior against the
current HDL, and retain the 32 MHz constraint for a fresh build. Compiler success
alone does not admit a physical trial. Attempt002 remains a separate failed
verification episode; neither failure is erased.
