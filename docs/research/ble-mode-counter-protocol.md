# Bounded advertising-mode counter diagnostic

Prospective, 2026-10-02; no physical result is implied. This addresses the
nonzero-MaxEvents zero-count discrepancy documented in the
[counter follow-up](ble-source-counter-followup.md). It does not qualify an
SDR source or change the existing counted-source protocol.

Run exactly one legacy episode followed by exactly one extended episode.
Change only event properties `0x0010` → `0x0000`. Both use owned handle 1,
primary map 1, primary/secondary LE1M, secondary skip zero, requested 20 ms,
the existing exact 16-byte owned AD, Duration 500 (five seconds), MaxEvents
255, and a one-second start delay. Extended mode makes secondary settings
operative and puts the marker in auxiliary data; this compares modes rather
than isolating one internal controller mechanism. No RF reception claim is
possible without a separately established extended-capable receiver.

Before operation, freeze and independently review the helper, wrapper and
protocol. Confirm the same Intel HCI0 USB identity, powered state and zero
active BlueZ advertisements read-only. Reserve handle 1 exclusively using
the earlier operator's established ownership; zero ActiveInstances alone
does not prove an unknown dormant set is free. Use the shared hardware
operator lock. If identity or ownership is uncertain, do not send commands.

The existing container wrapper supplies a finite duration-plus-margin deadline,
exact-name removal and socket release. Start the sanitized independent monitor
first and require its validated-header readiness. One helper invocation per
condition may send only parameters/data/enable and scoped disable/remove.
Retain original sanitized source JSONL and monitor metadata, exact script/image
hashes and return codes. Require matching typed parameter/AD/enable fields,
five command completions, one actual terminal status/count, and successful
disable/remove acknowledgements, socket closure, owned-container absence and
whole local process-group closure. Do not proceed to the second episode after
any rejected command, absent termination, timeout or unknown cleanup. Preserve
the failed prefix; no retry, fallback or controller repair.

No ESP firmware, UART, address, discovery, global event mask, power, reset,
kernel configuration or foreign advertising set is touched. Remove the monitor
container and reap its producer after the pair, retaining its terminal receipt.
The total pair supervisor deadline is 60 seconds, including monitor startup;
each source retains its existing finite command and duration margins.

Keep duration status `0x3c` and count-limit status `0x43` distinct. Five seconds
at the requested interval does not guarantee 255 events. A positive extended
count with another zero legacy count supports a mode-associated reporting
difference. Two zeros remain unresolved. Rejection is a retained diagnostic
outcome. Source/monitor agreement observes one controller, not two RF counters.

The extended option is accepted only for this bounded profile. Default legacy
wire bytes and the original status/count gate remain unchanged. Existing
counted-source reports must refuse extended configuration. No result supplies
channel-37 marker emission counts, rates, three repeated RF responses, a fresh
hidden-SDR positive or permission to run withheld Trial B.

Proof: frozen-source tests followed by the two actual sanitized receipts and an
independent exact replay of their command, termination and cleanup agreement.
Record a compact public numeric summary; keep raw capture/control files private.
