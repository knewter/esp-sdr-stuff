# Supplemental picotool preflight review

**PASS** for author revision `dcd116566f16c97808609be205a797a8c2b8dcd7`.
This corrects the hardware-free version-banner check after actual preflight
rejected the installed tool's `v2.3.1` prefix. The earlier
[lifecycle review](../forgix-usb-ram-lifecycle-review/README.md) stays unchanged.

A separate review worktree replayed all **29 lifecycle tests** using
`nix develop --command task forgix:usb-ram:trial:test`, including the actual
locked Nix executable. Its `version` command returned 0, empty stderr and
`picotool v2.3.1 (Linux, GNU-15.3.0, Release)`. Ten additional independent
wrong-version, suffix, unrelated and multiline banner cases were refused;
a nonzero command with the expected banner was also refused.

[checks.json](checks.json) binds the reviewed source, tests, executable and
private independent probe. Diff review confirms unchanged image/SDK/closure,
ELF, identity, preservation, lock and recovery guards. The new function uses
the fixed `version` command, a ten-second timeout and successful-exit check,
then requires the exact version token with optional parenthesized metadata.

No device, Docker, serial, RAM load or flash operation occurred during review.
This software correction does not supply physical USB throughput or recovery
evidence; those remain with the exclusive operator. No original hardware gate
or artifact whitelist changed.
