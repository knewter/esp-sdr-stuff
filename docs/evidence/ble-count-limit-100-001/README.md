# Actual 100-event legacy count diagnostic: count unavailable

On 2026-10-02 the root operator ran the separately declared single legacy
100-event source episode. Both original source and independently parsed monitor
recorded duration termination **`0x3c` with completed count 0**. The count gate
failed; the source and outer Task exited **2**. All five scoped commands were
accepted, cleanup completed, and controller identity/state remained unchanged.

| Fixed condition / observed result | Value |
| --- | --- |
| Advertising | Legacy nonconnectable/nonscannable, properties `0x0010` |
| Owned set / primary map / PHY | Handle 1 / map 1 / primary and secondary LE1M |
| Requested interval / duration / maximum | 20 ms / 5,000 ms / 100 events |
| Source records / monitor records | 23 / 11 |
| Accepted commands | Parameters, exact owned data, enable, scoped disable, scoped remove |
| Source and monitor actual termination | `0x3c/count0`, matching |
| Host enable acknowledgement → termination | 5.047042058 seconds |
| Full monitored episode | 35.145672479 seconds, below 60-second supervisor |
| Source socket, containers, producer and owned groups | Closed and independently verified |
| Adapter state before / after | Powered, zero active advertisements, unchanged |

The source image was preloaded from its exact immutable archive; both source and
monitor runtime IDs were verified. All 22 frozen project inputs remained
unchanged. Private directories/files retain 0700/0600 protection. The original
logs and receipts remain private; the [sanitized result](results.json) records
their hashes, software provenance and explicit unknowns.

The [prospective protocol](../../research/ble-count-limit-100-protocol.md) chose
100 instead of 255 because the earlier 20-ms/255-event profile cannot normally
reach its last event inside five seconds. This actual failure shows that timing
mismatch is not the whole explanation. It does not identify the firmware cause.
The actual zero field is not accepted as an emitted-event denominator; source
and monitor observe one controller rather than two independent RF counters.

No ESP UART, flash or receiver capture was used; Forgix firmware and FPGA were
untouched. No RF reception, detection rate, original 255-event qualification,
three-cycle RF response or Trial B prerequisite follows. No automatic retry,
fallback, reset, event-mask, power or discovery change was performed.

[Independent original-receipt review](../ble-count-limit-100-independent-review/README.md)
and [actual checks](../ble-count-limit-100-independent-review/actual-001-checks.json)
accept the retained failure and cleanup, not the count gate.
