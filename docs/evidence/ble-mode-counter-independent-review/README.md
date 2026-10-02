# Independent replay: both mode counts remain zero

The original private source logs, monitor metadata/log and lifecycle were
independently replayed without invoking the operator's validators or touching
hardware/Docker. [Checks](checks.json) bind source commit `d0be7b0` and hashes.
All 19 frozen inputs and four recorded private-file digests match.

Both modes retain `0x3c/count0`, five accepted commands, acknowledged scoped
cleanup, socket/container closure and actual helper exit2. All 22 monitor records
agree. Source 0's whole group closes before source 1 starts; the monitor producer,
container and group close. Pair 32.826581557s is below 60s. Actual start delays are
1.000118471/1.000120437s. Controller identity/state remain unchanged.

Independent saved Docker-archive config/hash checks reproduce both pinned image
IDs without querying Docker. The [public capture](../ble-mode-counter-001/capture.json)
reproduces the original numeric fields and file hashes exactly. Root's completed
source-diagnostic classification preserves each helper's failed count gate.
This single pair finds no mode-associated reporting difference; emission counts,
RF cause, extended-marker reception and Trial B qualification remain unproven.

Private replay source/result are retained under the review worktree's
`.scratch/counter-review/actual.py` and `actual-checks.json`; repeat with
`nix develop --command task -t .scratch/counter-review/Taskfile.yml actual`.
