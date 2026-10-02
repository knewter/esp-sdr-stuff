# Separate bounded monitor startup and capture timers

Implementation checkpoint, 2026-10-02. The actual
[extended100 episode](../evidence/ble-extended-count-limit-100-001/README.md)
retains matching `0x43/count100` records but fails normal monitor completion.
[Independent timing review](../evidence/ble-extended-count-limit-100-independent-review/actual-001-review.md)
reproduces how producer startup consumes the previous shared timeout. That
mechanism is plausible for the actual failure, not a proved dumpcap timer cause.

The monitor now offers explicit `--readiness-timeout SECONDS`. Omitting it
preserves the existing timing policy. With it, validated DLT254 header readiness
must arrive within the separate startup budget; missing/late readiness fails
with `startup_deadline`. Capture then gets its requested duration plus the
existing five-second grace, within an absolute active bound equal to startup +
duration + grace. Additional packets cannot restart that timer.

For a prospective 10-second startup and 30-second capture, the active bound is
45 seconds. This covers producer startup and reading, not Nix/Task/image loading
before the producer supervisor starts. Exact-container removal and process
reaping retain their separate finite cleanup waits; an outer operator deadline
and cleanup verification remain necessary. Receipts explicitly record phase
deadlines, startup elapsed time and the active bound. They do not claim all
cleanup fits inside that bound.

Both native and scoped-container entry points validate the new finite 0.1–60
second option before launching a producer or loading an image. Malformed pcap,
truncation accounting, record limits, cancellation, successful producer exit and
verified scoped cleanup remain required. The underlying dumpcap interface,
30-second autostop command, image, capabilities and privacy policy are unchanged.

Offline proof command:

```sh
nix develop .#ci --command task capture:ble-monitor:test
```

Synthetic real subprocesses reproduce delayed startup versus the old timer,
then verify completion with the explicit policy. Silent startup, post-header
hangs, invalid total budgets, cancellation on either side of readiness, and
unverified cleanup still fail and reap the producer. These checks open no
hardware or Docker container.

No fresh hardware trial has used this option. The original source-only caller,
freeze and failed receipts stay unchanged. Before a new operation, declare a
separate prospective caller/protocol, freeze all changed helpers and deadlines,
and independently review the complete lifecycle. This host correction supplies
no RF denominator, detection rate, FPGA measurement or task acceptance.
