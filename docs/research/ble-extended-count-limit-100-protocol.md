# One matched extended 100-event controller-count diagnostic

Prospective protocol, 2026-10-02. Run one source-only episode after independent
preflight review. No receiver capture or original acceptance criterion changes.

## Reason for this distinct condition

The [actual legacy 100-event trial](../evidence/ble-count-limit-100-001/README.md)
ended at `0x3c/count0` despite its count limit having room inside five seconds.
The [earlier mode pair](../evidence/ble-mode-counter-001/README.md) also reported
zero in extended mode, but requested 255 events: 254 intervals at 20 ms already
require 5.08 seconds before the last event completes. That extended condition
does not test whether a reachable nonzero limit works in extended mode.

This episode changes only advertising mode relative to the completed legacy
100-event condition. Its public helper change narrowly admits extended100
alongside the existing extended255 profile; tests must prove legacy wire bytes
and original counted-report refusals unchanged. All older failures remain.

The [official HCI §7.7.65.18](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html#UUID-b7eedd85-4369-f88f-7872-7278f7778cd2)
defines completed transmitted-event reporting for both modes with nonzero
MaxEvents. [Link Layer §4.4.2.2.1](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/low-energy-controller/link-layer-specification.html)
defines the 0–10 ms advertising delay. Without omissions, 99 × 30 ms = 2.97 s
between first and last starts, plus completion; this is a test rationale, not
a transmitted count or scheduling guarantee.

## Fixed profile and frozen preflight

Exactly one episode: owned handle 1, extended nonconnectable/nonscannable
properties `0x0000`, primary map 1, primary/secondary LE1M, secondary skip zero,
20-ms interval bounds, exact existing 16-byte owned manufacturer AD, Duration
500 units (5,000 ms), MaxEvents **100**, start delay **one second**.

Use a new private caller/Task and fresh result directory, separate from legacy
and old mode-pair inputs. Freeze this protocol, caller, Task, tests, every
transitive project module, public Taskfile, flake/lock, source/monitor helpers,
source and monitor image archives, configuration/executable hashes and recursive
Nix closure bindings. Review the complete freeze before hardware. Preloading
an exact source archive is offline preparation, not an HCI operation.

Root alone holds the shared operator lock. Confirm HCI0's stable Intel USB
identity/topology, powered state, zero active BlueZ advertisements and established
exclusive ownership of handle 1. ActiveInstances zero alone does not enumerate
dormant sets. Immediately before the single source launch, recheck identity,
state and frozen input hashes; the source then uses its fixed bound socket.
Uncertain identity/ownership or changed inputs means no source command.

Start the independent sanitized monitor first; require validated-header
`MONITOR_READY`. Monitor lifetime is 30 seconds. An absolute 60-second supervisor
covers startup, the sole episode and monitoring, followed by bounded cleanup.
Retain failed private prefixes. No sweep, second condition, retry, fallback,
repair, controller reset or global mutation is permitted.

## Actual result and cleanup gate

Only five commands: parameters, data, enable, owned-handle disable and remove.
Require five typed status-zero completions, exact profile/AD/enable agreement,
23 source records and exactly 11 monitor records (five command/completion pairs
and one actual termination). Termination follows accepted enable and precedes
cleanup, with identical typed status/handle/count in both original records.

Success requires actual status **`0x43`**, completed count **100**, source exit
0 and all lifecycle checks. Duration termination, including `0x3c/count0` or
`0x3c/count100`, remains failed; retain source/parent exit 2 and explicit
`actual_controller_limit_verified=false`, `source_gate_failed=true`. Missing,
duplicate, synthetic, boolean or mismatched counts do not qualify. Do not infer
a termination from elapsed time, requested maximum or accepted enable.

Require successful scoped disable/remove, source-socket closure, exact owned
source-container removal without force, monitor completion/producer reap and
owned-container removal, and closure of every owned child group. Recheck
controller identity/state and frozen inputs afterward. Unknown cleanup or
rejected commands stops further operations. No address, discovery, event mask,
power, global kernel configuration, foreign set, ESP UART/firmware or Forgix
MCU/FPGA changes are involved.

## Interpretation and proof

A positive count verifies reporting for this one extended100 episode. Source
and monitor see one controller; independently observed air emissions remain
**unknown**. Extended AD is carried on auxiliary channels, so this cannot
supply the legacy channel-37 marker denominator or qualify the original
255-event receiver reports. Neither outcome computes a detection rate, captures
a new hidden-SDR packet, supplies three repeated RF responses or releases Trial B.

Proof comprises meaningful synthetic refusal/success fixtures, independent
frozen preflight, one actual original source/monitor/lifecycle episode, and
independent replay. Publish sanitized numeric outcomes and hashes; retain raw
private records and every previous failure.
