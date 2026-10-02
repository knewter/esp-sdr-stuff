# Actual extended100 report: count observed, monitored episode failed

On 2026-10-02 the single matched extended-advertising episode produced an
actual **`0x43/count100`** termination in both the source and sanitized monitor.
The source passed its strict count check, exited 0, acknowledged scoped cleanup
and closed. **The complete monitored trial remains failed:** the monitor reached
its host deadline, removed its container and reaped a producer with exit 137.
The parent correctly refused success and exited 2. No automatic retry occurred.

| Boundary | Actual outcome |
| --- | --- |
| Fixed profile | Extended properties `0x0000`, handle 1, map 1, LE1M, 20 ms, duration 5,000 ms, MaxEvents 100 |
| Source records / monitor retained records | 23 / 11 |
| Command/completion agreement | Five matching pairs, all status zero |
| Actual source / monitor termination | Both `0x43`, completed count 100 |
| Host enable ACK → termination | 2.431111487 seconds |
| Source return / cleanup | Exit 0; owned disable/remove, socket and exact container closed |
| Monitor result | `host_deadline`; producer 137, producer reaped, exact container removed |
| Parent / full diagnostic gate | Exit 2 / failed |
| Trial start → last owned group closure | 38.932469611 seconds; no successful trial-end timestamp invented |
| Controller and inputs afterward | Identity/state unchanged; all 22 frozen inputs unchanged |

The source and monitor used the exact preflight-reviewed immutable images.
All owned groups closed; no cleanup failure is recorded. The adapter remained
powered with zero active advertisements. Original private receipts retain
0700/0600 permissions; the [sanitized result](results.json) binds their hashes
and preserves both the observed count and failed full lifecycle gate.

This distinguishes the controller's extended report from the separately
retained [legacy100 `0x3c/count0` result](../ble-count-limit-100-001/README.md).
It establishes an actual extended-event count report in this episode, not a
completed monitored protocol, an independently observed RF counter, or a
firmware explanation for legacy behavior. Both readers observe one controller.
Extended manufacturer AD uses auxiliary channels; this cannot supply the
original legacy channel-37 marker denominator or qualify the 255-event reports.

The frozen monitor gives a 30-second producer a host limit measured from
process launch plus five seconds. Readiness arrived after more than five seconds
of inferred startup, making startup/deadline competition a plausible explanation.
The exact internal start timestamp was not saved; this inference is not a
proved cause. Preserve the failed monitor and review timing offline before
declaring any fresh operation. Successful control records do not waive monitor
completion, producer-exit or cleanup requirements.

No ESP UART/capture/flash, Forgix firmware or FPGA operation occurred. There is
no detection rate, new SDR packet, three-cycle RF response, calibrated gain or
Trial B prerequisite. The [prospective protocol](../../research/ble-extended-count-limit-100-protocol.md)
and [independent preflight](../ble-extended-count-limit-100-independent-review/README.md)
remain separate from this actual failed episode.

[Independent actual review](../ble-extended-count-limit-100-independent-review/actual-001-review.md)
verifies the original records, accepted commands, complete cleanup and truthful
failure. Its synthetic timing reproduction tests a deadline mechanism without
substituting it for the hardware outcome.
