# Independent Efinity bootstrap review

PASS for implementation commit `8a3e2eae99c246d43554cc21e4a46a6cef396a7e`. [checks.json](checks.json) binds the reviewed helper/tests and private proof. This is an offline software checkpoint; it does not establish vendor licensing, gateware compilation or FPGA behavior.

The locked Nix/Task run passed all 30 project tests. Independent disposable fixtures passed 31 cases: original download preservation; private opaque license storage; atomic version selection and idempotency; corrupt/hash/version refusals with failed install retention; contained internal symlinks; traversal, link-pivot, hardlink, special-file and oversized metadata refusals; member/expanded-size/free-space limits. The earlier staged-parent symlink escape now refuses without changing the external sentinel.

Four additional injected checks passed automatic current-installation resolution, explicit environment precedence, unchanged HOME, and unknown-group-closure refusal before installation lookup or subprocess launch. Project fixtures also verify cancellation during spawn, real process timeout cleanup, and closure-marker refusal for storage and host-check reuse. Captured vendor output remains private; compilation forwarding through the public host-check is refused. The existing physical device/clock/revision gates and Nix FHS wrapper were unchanged.

Actual hardware-free Forgix Task checks returned `host_ready`, refused missing vendor installation and host-check compilation forwarding, and discovered one completed software candidate plus one unopened partial download. No actual vendor command or hardware operation was performed by this reviewer.

The [official installation guide](https://www.efinixinc.com/docs/efinity-installation-v4.1.pdf) documents separate Linux full releases and patches, setup scripting, and vendor user logs under `~/.efinity`. It does not establish a license destination. The helper consequently accepts only an explicitly supplied destination from the user's vendor instructions. Actual vendor CLI, license activation/compile, and vendor HOME log permissions remain unverified here; these need legitimate installed inputs and separate evidence.

Reproduce project tests with `nix develop .#ci --command task forgix:efinity:test`. Private independent fixtures use `nix develop .#ci --command task -t .scratch/efinity-review/Taskfile.yml independent`; hardware-free integration guards use the same private Taskfile's `integration` task in `.#forgix`. The private scripts and results are bound by SHA-256 in the receipt.
