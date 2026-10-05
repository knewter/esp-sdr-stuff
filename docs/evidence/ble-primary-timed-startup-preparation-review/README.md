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

Source165/45, monitor75/80, caller30, native32 and outer300 limits are unchanged;
the receiver's original bounds and qualification gates also remain unchanged.
Existing profile/wire, CID, inherited-lock, archive/NAR, restoration and natural
closure checks remain required. Historical qualification replay helpers retain
their exact bytes. No automatic retry or profile fallback is added.

**Next gate:** fresh whole root transfer, runtime/content proof, timing and current
endpoint/controller/image admission, followed by an independently reviewed
actual timed-source qualification. Receiver admission remains conditional on
that original saved source proof. These host results supply no source
qualification, RF observation, air denominator, calibrated timing or physical
task acceptance. The [original timed plan](../ble-primary-timed-plan-review/README.md)
and original Trial B gates remain open.
