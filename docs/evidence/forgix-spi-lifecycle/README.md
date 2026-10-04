# FPGA lifecycle controller: offline policy and real process checks

October 3, 2026 (local). **Twenty checks pass, with no skips. No hardware port
was opened, FPGA programmed or RAM bridge loaded.** The [receipt](checks.json)
binds committed source, test duration and the private log hash. This is
own-operator host evidence; there was no independent-agent review this turn.

The [controller and worker wrapper](../../../tools/forgix_spi_lifecycle.py)
advance preparation for task 2.1. There is **no physical backend, FPGA
configuration writer or load/program CLI**. Injected adapter receipts and
clocks test lifecycle policy; they do not prove real preservation, configuration
continuity or recovery. Real process tests hold only regular files and a private
flock. OpenSpec remains **1/5 physical acceptance tasks complete**.

```sh
nix develop .#ci --command task forgix:spi-bridge:lifecycle:test
nix develop .#ci --command task forgix:spi-bridge:lifecycle:plan -- \
  --plan .scratch/forgix-lifecycle-plan-001
```

## Session policy now implemented

The controller models qualification, fresh full preservation, an explicit
configuration strategy, identity-selected ROM/RAM loading, configuration
transition verification, the finite collector, worker closure and fresh
factory/full-flash verification. Both configuration strategies are tested:
qualified retention through startup, or exact-image configuration after RAM
startup. The current bridge has no configuration writer, so that second path
still needs reviewed firmware/protocol implementation.

The 600-second session reserves 325 seconds for factory return, full
preservation and final checks. Each operation receives a capped absolute
deadline. Private intent records precede possibly consumed requests. A lost ROM
or load acknowledgment still requires recovery. Invalid qualification or
preservation prevents the first mutation; the modeled preservation requires
two complete 2 MiB hashes, the original MCU identity, independent device
comparison and factory application verification.

The controller rejects mismatched RAM/FPGA/source identities, CDONE without
configuration continuity, failed prefix persistence, missing scratch
restore/readback or missing FINISH. Closure uncertainty prevents all further
worker/device access, including recovery. Ordinary failed/cancelled collection
still attempts modeled factory/full-flash verification after closure. Changed
frozen inputs or failed cleanup retain failure/manual-recovery state. Late or
unpersisted terminal receipts cannot report model completion.

These checks validate receipt matching and ordering. The future physical
adapter must produce those receipts from measured operations and bind the
reviewed artifacts, device identity, pinned toolchain and actual electrical
qualification. Setting a receipt flag is not physical evidence. The controller
always labels results `model_policy_only` and leaves physical execution and
qualification unadmitted.

## Actual worker ownership checks

`WorkerOwner` uses the existing RAM trial's spawn-cancellation protection and
whole-process-group cleanup. It validates the inherited exclusive flock,
retains a private 0600 log, caps worker count and rejects expired or late
completion. Unknown closure blocks later spawning, including when closure
marker persistence failed. It never unlocks or closes the caller's lock.

The [tests](../../../tests/test_forgix_spi_lifecycle.py) run actual Nix Python
children to verify lock inheritance, timeout and process disappearance. A
disposable subreaper test lets a leader exit while a descendant holds a regular
file and ignores SIGTERM. The worker returns only after that descendant is
killed, reaped and its descriptor owner is gone. Cancellation at spawn is also
injected through the existing ownership helper. None of these fixtures opens
a serial or USB device.

## What remains before physical register readback

Qualify FPGA grade, actual clock and pin handoff; resolve configuration across
the [audited SDK startup resets](../forgix-spi-bridge/README.md); implement and
review the physical backend/configuration path; then obtain fresh preservation
before any load. The [private collector](../forgix-spi-collector/README.md) is
tested separately. The accepted ledger and four remaining hardware task
checkboxes are unchanged. Earlier physical USB measurements and failed episodes
remain available.
