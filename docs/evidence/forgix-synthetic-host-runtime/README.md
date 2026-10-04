# Synthetic host-runtime review

October 4, 2026: **PASS for the offline runtime addition only**.
[Checks and source hashes](checks.json) bind 14 runtime and 35 existing lifecycle
groups, seven independent groups, and fresh actual verification of 63 committed
inputs, seven selected tool executables, 268 Nix paths and 1,097 reference edges.
The mapped root checkpoint is `19f0ffc`; the isolated author freeze is `f6fe601`.

Python, picotool, Git, Nix, nix-store, Docker and selected Task now have exact
store paths, resolved targets and byte hashes. Inherited dispatch uses bounded
store bin directories and the explicit local Docker socket. Complete Nix
closure contents are verified. Independent review found that deleting a
referenced libpsl node was previously accepted; the retained failure prompted
mandatory canonical reference metadata and graph completeness checks. The
corrected actual graph and omission probes pass.

Docker/Nix daemons, live kernel, udev, filesystem and pre-Python launch remain
trusted boundaries. Selecting Task does not prove its ancestor invocation.
No hardware, container producer, ARM compiler or vendor build ran. The
qualification registry remains empty; modeled/artifact proof does not qualify
physical grade, clock, voltage, pin timing, loading or throughput.

## Separate factory-return correction plan

The peer also found a concrete existing route defect: the synthetic backend
requests `returned-after-stream`, while the shared bounded query worker accepts
only `initial`, `returned` and `returned-after-ram`. This source mismatch blocks
factory-return verification if the unqualified route is eventually enabled.

Change only the synthetic call to the existing `returned-after-ram` label. The
stream runs in RAM and returns to the factory application, matching this helper
contract. Preserve the shared helper and old routes. Add a regression that sends
the backend's actual label through the actual query-worker admission and verifies
bounded dispatch/recovery wiring without opening hardware. Preserve the old
refusal. Fresh root freeze and independent correction review precede any claim
of full route preparation; physical qualification remains mandatory.
