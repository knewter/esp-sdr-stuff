# One bounded 100-event controller-count diagnostic

Prospective protocol, 2026-10-02. This is a source-only diagnostic, before any
hardware result. It does not replace the existing 255-event counted-source
protocol or change RF/burst acceptance criteria.

## Why this condition differs

The [previous five-second mode pair](../evidence/ble-mode-counter-001/README.md)
requested 255 events at a 20 ms interval. The earliest 255th start requires
254 × 20 ms = **5.08 seconds**, before completing that event. Thus the
five-second duration can expire before the count limit even without delay.
Bluetooth also adds 0–10 ms to each interval. This explains why that profile
can end by duration; it does **not** explain a zero completed count with a
nonzero maximum-event request. The official [Link Layer §4.4.2.2.1](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/low-energy-controller/link-layer-specification.html)
defines interval/delay timing; [HCI §7.7.65.18](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html#UUID-b7eedd85-4369-f88f-7872-7278f7778cd2)
requires the completed transmitted-event count when MaxEvents is nonzero at
either duration or count-limit termination, for legacy and extended advertising.

Earlier [duration-zero smoke trials](../evidence/ble-counted-source-smoke/README.md)
already tried short count limits. They remain separate failures:

| Request | Duration units | Host enable completion → scoped disable sent | Actual termination records |
| --- | --- | --- | --- |
| 255 events, 20 ms | 0 | 12.651 s | 0 |
| 10 events, 20 ms | 0 | 5.301 s | 0 |
| 10 events, 100 ms | 0 | 6.101 s | 0 |

These intervals subtract source `command_complete` for enable from
`command_sent` for cleanup disable; they are host observations, not RF timing.
A duration-timer explanation therefore cannot account for all retained failures.
Do not repeat those conditions as a fallback.

For 100 requested events, 99 × (20 + 10) ms = **2.97 seconds** between first
and last starts, plus event completion, absent omissions. That leaves room
inside the five-second limit. Scheduling may omit events or packets to serve
other controller functionality; the [Link Layer §4.4.2](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/low-energy-controller/link-layer-specification.html)
allows this. Arithmetic is a reason to test, never a measured count or guarantee.

## Fixed single condition and preflight

Run **exactly one** legacy episode: owned handle 1, event properties `0x0010`,
primary map 1 (channel 37), primary/secondary LE1M, secondary skip zero,
requested interval bounds 20 ms, exact existing 16-byte owned manufacturer AD,
Duration 500 (5,000 ms), MaxEvents **100**, and one-second start delay. There is
no extended-mode condition, sweep, retry, fallback, reset or repair.

Use the locked Nix shell and a private Task/caller copied separately from the
old mode-pair caller. Independently review and freeze this protocol, private
caller/Task, imported helpers, public Taskfile/flake/lock, source and monitor
helpers, and the immutable Nix source-image archive/ID. Loading the exact image
archive is offline preparation; it does not open an HCI socket. The existing
preload helper constructs a guarded 255-event argv during its offline check;
that construction does not launch a source or transmit 255 events.

The root operator alone owns HCI operations and the shared hardware lock.
Confirm Intel HCI0 USB identity/topology, `Powered=true`, zero BlueZ active
advertisements, and the earlier exclusive reservation of handle 1. Zero active
instances does not enumerate unknown dormant sets. If identity or ownership is
uncertain, send no commands. Recheck identity, adapter state and frozen input
hashes immediately before the one source-child launch; the unchanged source
helper then binds its socket for the episode. This is not a claim that USB sysfs
is reread before each of the five in-child command packets.

Start the independent sanitized monitor first and require validated-header
`MONITOR_READY`. The monitor lasts 30 seconds; an absolute 60-second supervisor
covers monitor startup, the single source episode and completion, with bounded
cleanup afterward. The source keeps its existing finite command waits and
five-second-duration-plus-margin termination wait. Keep failure prefixes private.

## Actual-result gate and cleanup

The source may send only parameters, data, enable, scoped disable and scoped
remove for its owned set. Require all five typed status-zero command completions,
exact parameter/AD/enable agreement, exactly one termination following accepted
enable and preceding cleanup, successful scoped disable/remove acknowledgements,
source-socket closure, exact owned-container removal and whole child-group
closure. The independent monitor must complete and retain exactly **11** records:
five matching command/completion pairs and the one matching actual termination.
Reap its producer and remove its exact owned container. Confirm controller
identity/state and frozen input hashes unchanged after all groups close.

Count-limit success requires actual typed status **`0x43`** and completed count
**100** in both original source and monitor records. Never construct a termination
from the request, elapsed time, enable acknowledgement or missing packet. Reject
boolean counts/statuses, mixed modes, mismatched source/monitor records, repeated
terminations, missing cleanup or unknown group closure. The source's own success
exit must be 0; the parent exits 0 only when this count gate and all lifecycle
checks pass.

A validly observed duration termination such as **`0x3c/count0`** remains a
failed count diagnostic. Retain source exit 2 and its exact error/cleanup summary,
explicit `actual_controller_limit_verified=false` and `source_gate_failed=true`;
the parent also exits 2. A completed monitoring/lifecycle episode is not a
successful count. Absent termination, rejected commands, timeouts or unknown
cleanup stop the operation with no further source attempt or global mutation.

No ESP32 flash/UART, address, discovery, global event mask, power, kernel setting,
foreign set, Forgix firmware or FPGA programming is involved.

## Interpretation and proof

A positive result verifies this controller's completed-event report for this
one 100-event episode. Source and monitor observe the same controller, not two
independent RF counters. Keep independently observed air emissions **unknown**.
No SDR capture occurs, so no reception count or detection rate is computed.
The original 255-event reports and qualification profile remain unchanged.
Neither outcome supplies three repeated RF responses, calibrated frequency/gain,
a new hidden-SDR packet or the original eight-bit prerequisite for Trial B.

Proof: frozen synthetic validator cases and independent preflight, followed by
one actual source/monitor/lifecycle receipt and independent exact replay. Publish
only a sanitized numeric summary, actual outcomes and file hashes. Preserve old
failures and raw private source/monitor/control records.
