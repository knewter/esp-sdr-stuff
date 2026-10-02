# Independent monitor timer review

Offline review passes the opt-in policy at source revision
`63212913bf925bfef2d4e9929c1ae54eb2f2cd2d`. This reviewer did not author
the monitor change. No Docker, Bluetooth, USB, serial or receiver operation ran.

The initial `f965c2260087a15f01bff4cba04ce7a387275d13` implementation
had a reproduced late-EOF defect: a scheduler delay could report `completed`
after the active deadline. The corrected source checks time after selector
return, packet parsing and finalization. The same synthetic producer now
reports `host_deadline` and is reaped; retained sanitized prefixes remain failed.
This does not retroactively accept the failed physical extended100 trial.

Locked Nix/Task replay passed all 26 project monitor tests and 10 additional
independent cases: invalid CLI/direct budgets before executable/image resolution,
both cancellation phases and handler restoration, missing cleanup/nonzero
producer, malformed/private data, late header/finalization/packet parsing,
no packet-based timer reset, and unchanged omitted/None shared-timer behavior.
The separate delayed-EOF reproducer also passes the failure classification.

Source inspection confirms the opt-in absolute bound is startup + capture +
grace, and READY follows validated DLT254 framing. Container capabilities,
mounts, dumpcap command and exact-name cleanup remain unchanged. Deadlines
classify delayed completion as failure; they do not promise a real-time scheduler
or instantaneous cleanup. This is software timing evidence, not RF, source-count
or loss-free monitoring proof. Hash-bound numeric details are in `checks.json`.
