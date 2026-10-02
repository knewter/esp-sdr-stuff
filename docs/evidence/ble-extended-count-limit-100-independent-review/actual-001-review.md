# Actual extended100 episode: positive source count, failed monitoring lifecycle

**PASS for integrity and truthful retention of a failed episode.** This does
not pass the full prospective diagnostic. Reviewed original source, monitor
and lifecycle receipts from revision
`a1eea40e2366c752cfdbe8b3939272c974a76e4d` on 2026-10-02.

The source's 23 records and monitor's 11 records agree on actual termination
status **`0x43/count100`**, after accepted enable and before scoped cleanup.
Five command/completion pairs match the exact extended100 profile. The source
returned 0 and verified disable/remove, socket closure and exact owned
container removal. Accepted-enable ACK to termination took **2.431111487 s**
on the source host clock; this is not an RF onset measurement.

The monitor envelope recorded **`host_deadline`**, producer return 137 and
elapsed **36.4367230910575 s**. Its Task returned 201. The required normal
monitor completion therefore failed, and the parent correctly returned 2 with
overall `status=failed`, `actual_controller_limit_verified=false` and
`source_gate_failed=true`. The nested source-only count observation remains
positive. The exact source/monitor record validator passed; the strict monitor
envelope validator correctly refused this result. Neither is substituted for
the other.

All owned groups closed without cleanup failures; the producer was reaped and
monitor container removed. Controller identity and powered/zero-active state
were unchanged. All 22 frozen inputs, both immutable image IDs, original saved
file hashes and private directory/file modes matched. No `trial_end` timestamp
exists because monitor waiting raised; start to last recorded group closure
was **38.932469611 s**, below the active supervisor limit. The
[machine-readable original checks](actual-001-checks.json) bind these facts.

## Bounded offline timing investigation

The current monitor host deadline starts before producer launch and is
`seconds + grace` (30 + 5 seconds here). The validated header arrived
**8.299199753 s** after outer monitor-child start, including Task and image
startup. Internal capture start has only a whole-second UTC value, so the
actual dumpcap timer start cannot be proven from these receipts.

An independent Nix/Task synthetic stdout producer demonstrated the timing
mechanism without Docker or hardware. A 0.03-second startup followed by
0.4-second post-header lifetime completed inside a 0.6-second host bound;
a 0.3-second startup with the same post-header lifetime hit that bound and was
reaped. The [synthetic timing receipt](synthetic-monitor-timing.json) is a
mechanism reproduction, not proof of the actual failure's internal cause.

A future monitor correction should give readiness its own bounded startup
deadline and give capture a bounded duration after validated readiness, while
retaining an absolute total limit and all cleanup/completion requirements.
It requires separate prospective review and frozen inputs before any new
physical episode. No original caller, freeze or actual receipt was changed;
no hardware retry occurred during review.

Both readers observe one controller. Independently observed air emissions are
unknown, extended auxiliary AD supplies no legacy channel-37 marker denominator,
and no detection rate, original 255-event RF gate or Trial B release follows.
The reviewer opened no hardware device or Docker container.
