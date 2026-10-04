# Zero-data extended-primary readiness preparation

This is offline preparation for one source-only controller-profile trial.
Independent preflight review and the physical source trial are pending. No
receiver, Bluetooth source, monitor container or device was opened by this
preparation. The existing legacy Trial B and RF reception gates remain open.

The [prospective protocol](../../research/ble-primary-zero-data-readiness-protocol.md)
was committed before implementation as `ad1eee73f364836adbc9d2b92a9e725e398a7c11`.
The scoped HCI acknowledgement change is
`d3dc8f5b6280644fa9ac6bbd39b56095cf7974b3`. The existing burst and spectrum plans
have a prospective appendix; their physical task checkboxes are unchanged.

The condition requests handle 1, extended properties 0, primary channel map 1,
LE 1M primary and secondary PHY, interval 20 ms, empty host advertising data,
100 maximum controller events, duration 5000 ms and start delay 0. It requires
the complete supported v1 parameter/data wire profile, five ordered successful
command/acknowledgement pairs and one matching termination with status `0x43`
and completed count 100 in both native and independently sanitized monitor
records. Missing, contradictory, duplicate, timer-expired or incomplete
receipts fail. Native configuration describes intent and cannot substitute for
the monitor's actual wire fields.

The new `0x2036` successful acknowledgement parser requires its exact five-byte
return shape and retains signed controller-selected transmit power in the
supported range −127 through 20 dBm. The two readers must agree. Requested
`0x7f` means no preference; selected power is controller metadata and provides
no calibrated RF measurement. Failed acknowledgements retain their previous
status-only shape; other acknowledgement records are unchanged.

The final locked Nix/Task replay passed **100 test groups**: 17 private caller,
24 HCI, 26 monitor/wrapper and 33 native-source groups, with no skips. Fixtures
exercise actual emitted HCI bytes, exhaustive selected-power bytes, truncated
and chunked transport, full profile mutations, ordering, actual host process
groups and locks, cancellation, late readiness/closure, durable-intent failures,
postflight refusal and fresh-process transitive imports. They use simulated
source/monitor transport and host-only processes. Earlier failing tests and
runtime-freeze attempts are retained privately.

The final isolated freeze contains 18 file inputs, eight immutable runtime
paths and 253 recursive Nix closure entries. A locked-flake Nix executable was
realized after the ambient executable and missing-store-path checks refused
the earlier attempts. Read-only Docker image inspection matched both archive
configuration identities; no image was loaded or container started. Exact
hashes, image identities and preparation bounds are in [checks.json](checks.json).

The private supervisor requires an already-held global operator lock, externally
reserved handle 1, current private USB/topology/BlueZ identity, powered and idle
controller, and identical postflight state. Its 75-second outer bound covers
monitor launch through validated readiness; the producer's separate readiness
bound is 15 seconds. Normal monitor capture is 30 seconds, grace is five seconds,
the active producer bound is 50 seconds, source parent cap is 40 seconds and
supervisor cap is 120 seconds. Deadlines cover spawn and post-operation checks.
Separate bounded cleanup must close native sockets, containers and whole owned
process groups. Forced, interrupted or uncertain termination cannot qualify.

The author freeze binds this isolated worktree's absolute paths and a private
historical identity reference. It does **not** admit a root execution. After
independent review, the sole root operator must copy the frozen private files,
derive and verify the current controller binding, reserve the handle, retain the
inherited exclusive lock and create a fresh freeze of the actual root inputs and
runtime before any source action. The private Task recipes support offline
testing, freeze and read-only image inspection:

```sh
nix develop .#ci --command task --taskfile .scratch/goal-primary-readiness-001/task.yml test
nix develop --command task --taskfile .scratch/goal-primary-readiness-001/task.yml freeze -- --controller-binding PRIVATE_BINDING --frozen-inputs FRESH_PRIVATE_FREEZE
nix develop --command task --taskfile .scratch/goal-primary-readiness-001/task.yml inspect -- --controller-binding PRIVATE_BINDING --frozen-inputs PRIVATE_FREEZE
```

A qualified source-only receipt would establish the requested controller profile
and its completed-event limiter. Controller events are not independently
counted radiated primary PDUs: primary omission, optional AUX/AdvA layout and
RF ownership remain observational questions. A future, separately frozen
three-repetition receiver trial at ten-bit/BW20/manual48 is conditional on that
source qualification and has not been implemented here. Neither this
preparation nor a future source-only success closes the original counted-air,
known-received-payload or reciprocal-response requirements.
