# Separate extended100 episode with explicit monitor readiness

**Prospective; no new hardware outcome.** This is a distinct source-only
follow-up to the [failed extended100 episode](../evidence/ble-extended-count-limit-100-001/README.md).
Its source and monitor both observed `0x43/count100`, but normal monitor
completion failed. Preserve that caller, freeze and result unchanged.

The only source/monitor operating change is the reviewed monitor's explicit
`--readiness-timeout 10` option, with its existing 30-second capture and
five-second grace. The producer supervisor has a 45-second absolute active
bound. This does not cover preceding Task/image startup or final cleanup;
those remain separately bounded. Default monitor timing stays unchanged.
See the [timer implementation and review](ble-monitor-readiness-timing.md).

A new private caller/Task uses a fresh result directory. Following bounded
offline source-image preload, the operator's 60-second supervisor covers
monitor launch, validated readiness, the sole source and normal monitor
completion. Outer validated-header readiness is limited to 15 seconds,
including Task/image startup; it is rechecked after the readiness helper
returns. No source launches after that or the supervisor deadline. Insufficient
startup allowance produces a retained failure, never a longer implicit timer.
After failure, existing finite exact-container and whole-group cleanup waits
still run; unknown closure prevents success. Cleanup is not represented as
occurring within the monitor's active bound.

Source settings remain exactly one owned handle-1 extended episode: properties
`0x0000`, map 1, primary/secondary LE1M, 20-ms interval bounds, the existing
16-byte owned AD, Duration 5,000 ms, MaxEvents 100 and one-second start delay.
No second condition, retry, fallback or controller-global mutation is allowed.
The existing [profile, identity and ownership rules](ble-extended-count-limit-100-protocol.md)
remain required. Root is the exclusive hardware operator; this preparation
opens no HCI, USB or serial device and runs no Docker container.

The new caller also requires actual explicit-policy receipt fields, finite
budgets, valid ordered phase timestamps and consistent bounded deadlines.
Missing/late readiness, boolean/nonfinite timing, old-policy receipts, failed
producer exit or incomplete cleanup remain failures. Require the unchanged
23 source records, 11 monitor records, five matching accepted command pairs
and identical actual termination after enable and before cleanup. Only actual
`0x43/count100`, source exit 0 and the complete verified lifecycle allow parent
exit 0. A typed duration diagnostic remains parent exit 2. Freeze the new
caller/Task/tests/protocol, every transitive input and exact runtime images
and closures before independent preflight; no automatic execution follows.

Focused offline proof reuses the prior typed count/cleanup fixtures and tests
explicit launch options, old/malformed/late phase metadata, delayed readiness
return, cancellation and unknown owned-group closure. New timing fields in
fixtures are synthetic, not replacement hardware evidence.

Both readers observe one controller. Extended AD uses auxiliary channels;
this supplies no independently observed air denominator, legacy channel-37
marker count, detection rate, new SDR decode or original Trial B qualification.
Original RF/count gates and every failed result stay unchanged.

Separate private entry points are `run_ble_extended_count_limit_100_ready.py`
and its `.task.yml`; output is a fresh `ble-extended-count-limit-100-ready-001`
ignored directory. Offline check:
`nix develop .#ci --command task --exit-code -t
.scratch/run_ble_extended_count_limit_100_ready.task.yml test`.
Only after freeze and independent review may the operator use the default
Nix shell with the same Task and `run`, preserving the parent exit code.
