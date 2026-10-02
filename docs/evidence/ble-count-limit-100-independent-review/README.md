# Independent 100-event preflight

PASS for the exact frozen [single-condition protocol](../../research/ble-count-limit-100-protocol.md). This review precedes hardware execution; all positive/count-failure validator fixtures are synthetic. The reviewer separately constructed source/monitor receipts and verified 27 refusal cases and exact scoped command bytes, then replayed all 19 author tests through Nix/Task.

The final 22-file freeze covers the 12 transitive project modules, including two imports added during review. Source/monitor archives, image configuration commands, executables and all 22/72 recursive NAR bindings were independently checked offline. Cancellation, readiness/deadline failure, uncertain group closure and postflight mismatch cannot qualify success. Task `--exit-code` preserves the parent's failed-count exit 2.

Only original matching typed `0x43/count100` records plus complete cleanup can pass the proposed diagnostic. Timing arithmetic is prospective rationale; no air-emission denominator, reception rate, 255-event qualification or Trial B release follows from this preflight.

Private replay in the review worktree: `nix develop .#ci --command task -t .scratch/count100-review/Taskfile.yml validators author-tests archives`. Ignored frozen inputs and private fixtures are required. [Bindings and numeric checks](preflight.json) identify the reviewed bytes.

## Actual episode 001

Independent replay accepts the original receipts; **the count diagnostic failed**. Both readers recorded typed `0x3c/count0`. Source exit 2, monitor exit 0, 23 source records, 11 monitor records and all five scoped command acknowledgements agree. The 22 frozen inputs, saved files, exact image IDs, private modes, readiness, controller state and socket/container/group cleanup passed inspection.

Host enable acknowledgement to termination was 5.047042058 s; the supervised episode took 35.145672479 s within its 60 s budget. These are host observations, not RF timing. Reducing the requested limit to 100 retained the zero-count duration outcome; it does not establish zero transmissions or identify a controller cause. Earlier failures remain unchanged, and no 255-event, RF or Trial B gate is released.

[Actual numeric checks and original-file hashes](actual-001-checks.json) bind source revision `3b33da9ad3de58dcfd528edfbda18a93a3afd063`. Private replay: `nix develop .#ci --command task -t .scratch/count100-review/Taskfile.yml actual`. Its parent return-code field states the expected gate result, consistent with the root operator's reported exit 2.
