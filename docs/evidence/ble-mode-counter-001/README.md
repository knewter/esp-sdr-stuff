# Both advertising modes retain zero controller counts

Actual source-only pair on 2026-10-02 from commit `d0be7b0`, using the
[declared bounded protocol](../../research/ble-mode-counter-protocol.md) and
[independently reviewed preflight](../ble-mode-counter-preflight-review/preflight.json).
Command: `nix develop --command task -t .scratch/run_ble_mode_counter.task.yml run`.
The private Task/caller hashes and original receipt hashes are in
[numeric capture](capture.json); neither script accesses an ESP port or flash.

Exactly one legacy episode (`0x0010`) and one extended episode (`0x0000`)
use handle 1, requested 20 ms, LE1M, primary map 1, the same owned AD,
five-second duration, MaxEvents 255 and one-second start delay. All ten
commands are accepted and all 22 independently monitored command/completion/
termination records agree. Both actual terminations are `0x3c/count0`.
Both helpers retain `trial_failed` and exit 2 under the unchanged count gate;
the pair completes only as a source diagnostic in **32.826581557 seconds**
against its absolute 60-second ceiling.

Scoped disable/remove acknowledgements, source sockets, exact owned source
containers, monitor container/producer and complete local child groups close.
Controller identity/state and frozen inputs remain unchanged. Original private
logs are retained; public evidence exports numeric fields and hashes only.

The proposed mode-associated counter difference was not observed. Zero is
still unusable as an emitted denominator. Extended AD occupies auxiliary data
and had no independent RF reference in this pair. No fresh SDR packet, rate,
three-pair RF response, calibrated signal or Trial B qualification follows.
The ESP firmware and preserved Forgix factory loader were untouched.

[Independent exact replay](../ble-mode-counter-independent-review/README.md)
checks all 19 frozen inputs, saved logs, original source/monitor records,
pinned image archives, elapsed budget and cleanup. It reproduces the public
numeric fields and verifies the original file hashes.
