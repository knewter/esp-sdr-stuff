# Primary receiver preparation in the root checkout

October 4, 2026: **read-only root preparation and independent saved-proof review
pass; no receiver experiment has run**. [Checks](checks.json) bind the exact
committed context and private proof. The [corrected author preparation](../ble-primary-receiver-preparation/README.md)
remains the implementation subject.

The root copied the reviewed private caller/support/fixtures without changing
their bytes and replayed all 161 host-only groups. A fresh snapshot at root
`8d13e7f` binds 69 input files and 11 runtime paths. Its complete Nix reference
graph contains 301 paths and 1,218 edges. The actual root `nix-store --verify-path`
operation verified the contents of every path and returned zero. Source and
monitor archive IDs match the loaded immutable images.

Under the exclusive operator lock, read-only checks found the original ESP32,
both matching original 4 MiB backups, the bound idle Bluetooth controller, a
root-owned local Docker Unix socket and no selected-image containers. No UART,
raw HCI socket, source producer or receiver was opened. The first attempt in the
CI shell refused its missing radio runtime bindings; that failure is retained.
The full project shell then passed.

Independent review rehashed all inputs, runtime files, saved operation receipts,
original backups and source qualification, independently derived the archive
configuration IDs, and checked the exact complete content-verification command.
Relative to the isolated author snapshot, only the unrelated root Taskfile
additions change an input hash; runtime, closure, receiver profile and images
agree. The reviewer inspected saved proof and made no live device or daemon calls.

This is static preparation. The [initial outer operator review](../admission-review-failures-001/README.md)
found defects requiring correction; merged input changes also require a fresh
explicitly reviewed snapshot.
At actual launch the holder must recheck current endpoint, controller, device,
images and ownership under the lock. Original restoration and whole experiment
closure require their own saved physical proof. Controller counts are not an
air-emission denominator; no radio task, original Trial B or accepted requirement
changes.

Daemon/kernel/filesystem state and the pre-Python launcher remain trusted.
Saved successful operator checks do not reconstruct kernel history, and selected
Task bytes do not prove an ancestor's invocation. Raw identities, firmware dumps,
environment and process receipts remain private.
