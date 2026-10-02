# Counted-source diagnostics: commands accepted, count unavailable

Three physical, **source-only** tests requested finite legacy LE1M advertising
on HCI0. All parameter, data, enable, own-handle disable and removal commands
received status-zero acknowledgements. Neither the source socket nor the
independent capture-capable Bluetooth monitor observed an Advertising Set
Terminated event. Each source timed out and closed successfully after cleanup.
**No actual completed-event denominator is established.**

| Requested event limit | Interval | Monitor duration | Monitor packets / retained controls | Actual completed events |
| --- | --- | --- | --- | --- |
| 255 | 20 ms | 20.148 s | 18 / 10 | Unknown |
| 10 | 20 ms | 15.143 s | 18 / 10 | Unknown |
| 10 | 100 ms | 15.179 s | 18 / 10 | Unknown |

These are diagnostics, not the predeclared `counted-01/02/03` receiver trials.
No ESP port was opened or firmware changed. Original GPIO firmware remains
restored. No new RF emission or reception claim follows from accepted commands.

## Fixed configuration and actual records

The [source helper](../../../tools/ble_direct_hci_source.py) uses reserved
handle `0xEF`, event properties `0x0010` (legacy, nonconnectable and
nonscannable), only channel 37 / 2402 MHz, primary and secondary PHY 1, and
the exact 16-byte owned manufacturer AD marker. Duration is zero; the event
limit is nonzero. No retries, restarts, global advertising clear, pairing,
scanning, controller power or event-mask changes were performed.

The temporary source container had a read-only script/root filesystem,
host networking and only NET_ADMIN/NET_RAW after dropping all capabilities.
The existing capture-capable `dumpcap` supplied a separate in-memory monitor;
no raw HCI, pcap, addresses or foreign payloads were saved.

Each directory retains the full sanitized source sequence, monitor, operation
logs and external BlueZ preflight/postflight:

- [255 events / 20 ms source](255-events-20ms/source-control.jsonl) and
  [monitor](255-events-20ms/hci-control.json).
- [10 events / 20 ms source](10-events-20ms/source-control.jsonl) and
  [monitor](10-events-20ms/hci-control.json).
- [10 events / 100 ms source](10-events-100ms/source-control.jsonl) and
  [monitor](10-events-100ms/hci-control.json).

All monitors completed with exit zero and reaped producers; all ten retained
records comprise five commands and five successful acknowledgements. No
termination was retained. All source helpers exited 2 with `event_timeout`,
then acknowledged handle-specific disable and removal and closed the socket.
BlueZ was powered with ActiveInstances zero before and after every trial.
Monitor drop counts and independent RF emission counts remain unmeasured.
[Provenance](provenance.json) pins the source/image/tool and every receipt hash.

## Interpretation and next gate

The [Core command/event semantics](../../../tools/BLE_DIRECT_HCI_SOURCE.md)
require an actual termination count; a requested maximum and a successful
enable are insufficient. The running kernel normally enables this event for
an extended-advertising-capable controller. Cached controller feature byte 1
is `0x59`, including extended advertising bit `0x10`. This is evidence of the
expected initialization policy, not a readback of the current event mask.

Event suppression or controller firmware/limiter behavior are unresolved
hypotheses. Standard HCI and the inspected kernel debugfs/sysfs expose no
current LE event-mask readback. A guessed global-mask overwrite cannot preserve
an unknown previous mask, so none was performed.

The [counted receiver protocol](../../research/ble-counted-trials.md) remains
ready for an independently recorded source counter, but its physical trials
remain pending. The earlier five CRC-valid owned packets still demonstrate
offline burst decoding. They supply no event hit rate. A source with observable
completed-event or independently measured emission counts is the next input.

[Primary-source analysis](../../research/ble-controller-count-limit.md) pins the
kernel initialization, missing readback and restoration constraints.
[Independent review](../ble-controller-independent-review/README.md) checks
all receipt hashes, actual wait durations, cleanup acknowledgements and the
offline reporting gates. It closes no physical receiver-count requirement.
