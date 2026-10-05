# Timed startup corrections: independent host review

Source003 and receiver004 pass independent offline review. They recheck the
**original** deadline inside deferred cancellation immediately before `Popen`.
Entering that context after the deadline, or exactly at it, now refuses without
launching. In-time harmless children retain ownership and close safely; the
source cancellation fixture signals only its fresh isolated process.

| Preparation | Author groups | Independent groups | Outcome |
| --- | ---: | ---: | --- |
| Source003 | 99 | 3 | Host preparation passes |
| Receiver004 and holder | 101 + 60 | 12 | Host preparation passes |

All final replays return0 without skips. The
[source003 prospective plan](../../research/ble-primary-timed-source-003-spawn-admission.md)
was committed as `9dfdf0c` before its private correction. [Checks](checks.json)
pin both exact readiness receipts, both independent receipts and the corrected
helpers. The private fixtures, logs, identities and module inventories stay
outside Git and the site.

Root replay now passes all 99 source, 101 receiver and 60 holder host groups.
The first receiver/holder root replays remain failed: the initial transfer
omitted their reviewed historical fixtures and kept operational files in
at-rest modes. Copying the 19 pinned fixtures and setting the required private
operational modes fixes the transfer without changing code or guards. Fresh
logs and result hashes are retained; these results remain host evidence.

The receiver003 late-entry failure, earlier receiver002 failures and their
immutable bundles remain retained. Source002, reviewed CID-helper ancestry and
the historical read-only benchmark remain unchanged. The
[actual timed source001 startup failure and reviewed recovery](../ble-primary-timed-source-001-failed/README.md)
remain separate: that attempt issued no source command. The new host preparation
does not rewrite those outcomes or the earlier accepted radio measurements.

Source165/45, monitor75/80, caller30, native 32 and outer300 limits are unchanged;
the receiver's original bounds and qualification gates also remain unchanged.
Existing profile/wire, CID, inherited-lock, archive/NAR, restoration and natural
closure checks remain required. Historical qualification replay helpers retain
their exact bytes. No automatic retry or profile fallback is added.

## Fresh preparation and timing refusal

At root revision `5c5ddfcb`, the read-only preparation exposed a lazy DBus
import: the historical snapshot requested 11 Nix roots, but actual preflight
requested 12. Loading the actual parent dependencies before freezing fixes
equality. A fresh full snapshot and second verification pass with 42 inputs,
12 runtime objects, 12 roots, 303 content-verified Nix paths and 1,220 reference
edges. Preparation took 53.796 seconds under its separate 120-second bound.
The recipe passes 12 author/root and 6 independent host groups.

The subsequent **partial read-only timing check refused**, returning 2 without
launching a source or monitor. Known frontwork took 31.198 seconds, including
30.806 seconds of full freeze verification; controller/image identities agreed
before and after. Within the original 45-second source clock, the native 32-second
reserve permits at most 13 seconds for setup. This run already exceeds that
allowance before live-monitor checks, process startup or native acknowledgements.
Independent saved review verifies this necessary refusal; it does not predict
a future run or qualify a source.

A separate 37.115-second diagnostic profile attributes 14.289 seconds to Nix
evaluation, 13.597 to full Nix contents and 6.233 to archive proof. These are
phase observations from another run, not combined operational-fit evidence.
Independent review confirms transparent hooks and saved attribution. Every
original verification ran; no limit was widened. Private receipts are
pinned in [checks](checks.json), with earlier failures retained.

**Next gate:** reduce verification cost while preserving fresh complete contents,
archive, input and selection checks, then prove current timing and whole root
admission before actual timed-source qualification. Receiver admission remains
conditional on that original saved source proof. These results supply no source
qualification, RF observation, air denominator, calibrated timing or physical
task acceptance. The [original timed plan](../ble-primary-timed-plan-review/README.md)
and original Trial B gates remain open.
