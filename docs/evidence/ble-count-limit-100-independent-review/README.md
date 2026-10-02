# Independent 100-event preflight

PASS for the exact frozen [single-condition protocol](../../research/ble-count-limit-100-protocol.md). This review precedes hardware execution; all positive/count-failure validator fixtures are synthetic. The reviewer separately constructed source/monitor receipts and verified 27 refusal cases and exact scoped command bytes, then replayed all 19 author tests through Nix/Task.

The final 22-file freeze covers the 12 transitive project modules, including two imports added during review. Source/monitor archives, image configuration commands, executables and all 22/72 recursive NAR bindings were independently checked offline. Cancellation, readiness/deadline failure, uncertain group closure and postflight mismatch cannot qualify success. Task `--exit-code` preserves the parent's failed-count exit 2.

Only original matching typed `0x43/count100` records plus complete cleanup can pass the proposed diagnostic. Timing arithmetic is prospective rationale; no air-emission denominator, reception rate, 255-event qualification or Trial B release follows from this preflight.

Private replay in the review worktree: `nix develop .#ci --command task -t .scratch/count100-review/Taskfile.yml validators author-tests archives`. Ignored frozen inputs and private fixtures are required. [Bindings and numeric checks](preflight.json) identify the reviewed bytes.
