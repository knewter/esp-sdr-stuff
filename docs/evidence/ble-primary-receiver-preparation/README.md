# Conditional three-repeat primary receiver preparation

The offline caller is ready for independent preflight review. No receiver trial,
Bluetooth source, monitor container, device, firmware build or vendor tool was
run in this preparation. Existing radio acceptance and original Trial B gates
remain unchanged.

The [prospective protocol](../../research/ble-primary-receiver-three-repeat-protocol.md)
was committed before implementation. It follows the independently reviewed
[source-only condition](../ble-primary-zero-data-source-001-review/README.md)
and binds that exact saved audit and all its original receipts. That source
qualification establishes controller profile/completed-event accounting; it
provides no independently counted primary RF transmissions.

The fixed receiver requests ten bits/component, nominal16 MS/s, 16,380 pairs,
LO2401 MHz, BW20 and manual48. The exact demonstrated UART921600 image is reused:
its manifest, build-info and three image hashes are fixed, so no new build is
needed if those bytes and actual setting ACKs match. Three separately logged
zero-data extended source instances each request handle1, 20 ms, MaxEvents100,
Duration5000 ms and start delay0. Each must retain the full supported v1 profile,
five successful command/ACK pairs, matching selected power and one0x43/count100
termination in native and monitor readers.

Receiver duration180 seconds and monitor duration240 seconds preserve a planned
10-second initial OFF baseline, two-second gaps after natural source-group
closure and a continuous final OFF tail strictly longer than10 seconds. Actual
baseline>=5 seconds and gaps>=1 second are separately checked. Clock limits
cover spawn, marker reads, durable source intent, lock recheck and whole-group
closure. A failed first condition cannot be repaired with a disjoint tail or
by dropping a repetition.

The caller preserves original two-read4 MiB backups, takes a fresh complete
pre-install readback, guards installation and verifies installed provenance.
After all owned UART groups close, it restores the full original flash, verifies
fresh readback and expected reset boot. Uncertain UART ownership blocks restore;
forced cleanup or failed restoration cannot qualify the condition. The inherited
exclusive global operator lock and current stable ESP/controller identity remain
mandatory. No discovery, pairing, power/reset or controller mask changes occur.

Prospective ownership instrumentation records private leader PID/PGID, process
start identity, spawn/closure brackets and actual command. The private dispatch
adds only a fresh `--cidfile` to the reviewed container command builder, observes
the exact Docker ID/name/image/running state while active and retains successful
exact-name absence after normal completion. Its witness must match the spawned
role/token and process bracket. Historical source-only IDs are not invented.

**161 offline test groups pass**: 39 private caller/accounting/dispatch groups,
19 primary parser, 20 prefix-retention, 24 HCI, 26 monitor/wrapper and33 native
source groups, with no skips. Tests use actual saved source/monitor receipts,
a saved ten-bit waveform with independent SHA/CRC/count checks, independent
synthetic CRC/modulation fixtures and owned harmless host process groups. They
exercise full profile corruption, source ordering, active container identity
fixtures, late deadlines, cancellation, durable-intent failure, forced cleanup,
restoration failure, raw corruption, guarded whole-packet joins and all-phase
cluster conflicts. The first permission-fixture failure is preserved privately.
Both OpenSpec changes validate.

The isolated snapshot freezes **69 files, 11 runtime paths and301 recursive Nix
closure entries**, including complete transitive imports, qualification receipts,
private address reference, receiver/preservation inputs and unchanged decoder
bounds. Read-only image inspection matches the frozen archive identities. The
[sanitized checks](checks.json) bind the exact private files and runtime receipt.
Root must copy those reviewed files and create a fresh freeze against its current
committed Taskfile, helpers, private binding and actual Nix runtime; the isolated
author snapshot cannot admit root hardware.

Offline replay and accounting are separate Task commands. They verify every
waveform before joining the entire host acquisition bracket to enable-ACK+100 ms
through termination-100 ms in both readers. Only complete CRC-valid type7 with
present exact private public AdvA can become an attributed primary candidate.
ADI-only, AUX AD, missing AdvA, conflicting clusters and incomplete waveforms
cannot become complete source hits. The public-AA search and refinement bounds
are unchanged; source labels do not train slicing. No reception rate, confirmed
RF misses or accepted radio gate is produced.

The opportunity is small: approximately1 ms windows with historical0.4–0.5 s
UART delivery may yield roughly15 ON snapshots across the three short episodes.
A hypothetical random-alignment calculation predicts fewer than one full hit;
it is not a measured schedule. Primary omission and AUX/layout variation add
uncertainty. This fixed first condition is retained, and a null remains
inconclusive. Future transport or capture improvements need a separate
prospective condition.

Run host checks from the isolated worktree:

```sh
nix develop .#ci --command task --taskfile .scratch/primary-receiver-001/task.yml test
```

The private Task also provides read-only `caller -- freeze`/`caller -- inspect`,
then an explicitly guarded operator-only run, fixed decoder replay and strict
accounting. Independent preflight and a fresh root execution freeze are required
before any physical action. No hardware task is checked by this preparation.

## Corrected readiness freeze

The first frozen preparation (`f301ebe`) failed independent review: a31-second
delay inside receiver-ready timestamp acquisition could return131 after its130
deadline and still launch all three sources in the host fixture. No hardware
ran. Exact original files, snapshot, failure receipt and probe output remain
privately archived; that freeze remains failed.

The replacement verifies observed and current clocks before/after timestamp and
helper return, then explicitly checks caller admission against applicable
receiver, monitor and supervisor limits before baseline/source action. Equality
to a deadline is rejected. Exact-boundary, delayed-stamp, delayed-return and the
original independent external-stamp probe now reject source launch and retain
restoration. Receiver-ready observation and phase/source deadlines are also
saved for subsequent receipt audit. The new test variable uses TEST_HOME.
Both OpenSpec validations and fresh read-only freeze/image inspection pass.
Independent replacement review and fresh current-root execution freeze remain
required; source/profile/search/settings/acceptance conditions are unchanged.

## Independent corrected preflight

**PASS offline at `120cf8a`**: the peer replayed all 161 author groups and seven
independent groups, with no skips. [Independent checks](independent-review.json)
bind exact source/test/Task/protocol/snapshot hashes and private terminal proofs.
The 69 input and 11 runtime files match their recorded bytes and hashes; the 301-path
metadata graph contains 1,218 complete reference edges. All 17 actual project
imports are frozen. This verifies isolated preparation, not the current-root
execution tuple or physical behavior.

The preserved `f301ebe` counterexample returned receiver-ready 131 after deadline 130
and incorrectly launched all three sources. The same independent host probe now
returns failure/exit 2, launches no source, and reports verified restoration through
the injected fixture. Neither probe touched hardware. Actual owned-process tests
also reject natural qualification when a surviving descendant needs forced
termination. Strict source/monitor fields, cancellation/intent failures, uncertain
UART ownership and guarded whole-capture joins pass the peer probes.

The independent replacement review is complete. **Root transfer, a fresh input/
runtime/content/image freeze and independent operator-wrapper preflight remain
required before hardware.** Full preservation, identity/exclusive FD, handle
reservation, restoration and physical saved-result review remain operator gates.
No receiver trial, primary air denominator, RF acceptance or original Trial B
release follows from these tests. Earlier failure proofs remain immutable.
