# Prospective native comparison of direct-HCI advertising limits

**UNVERIFIED: the six-episode comparison has not completed.** Native source-reference002 received
1176 exact owned reports using BlueZ, completed its explicit 90-second stop and
verified original-image restoration. The direct-HCI timer diagnostics instead
returned actual `0x3c/count0`; their previous SDR snapshots decoded no complete
owned packets. The new experiment asks whether the direct-HCI source is
receivable by the now-proven native observer, and whether the event limiter
changes that observed reception. It does not establish hidden SDR decoding,
count independently radiated packets, or release conditional Trial B.

Grounding: [native002](../evidence/native-ble-source-reference-002/README.md),
[timer diagnostics](../evidence/ble-duration-source-diagnostics/README.md),
[zero-counter RF trial](../evidence/ble-zero-counter-rf/README.md), and
[unchanged prospective BLE plan](ble-next-trial.md).

## Retained failed first run and prospective supervisors

Run001 stopped after its first source. The helper returned the expected
duration termination `0x3c/count0` and diagnostic exit 2, but the enclosing
Task returned 201. The original supervisor expected 2 and failed before
starting the remaining five episodes. Its original executed files remain
immutable; the comparison remains failed. The completed native receipt reports
[59 owned receptions](../evidence/native-direct-reference-001/capture.json),
and [full original-image restoration](../evidence/native-direct-reference-001/restoration.json)
verified. Those observations do not retroactively complete the six conditions
or qualify the SDR/count gates; independent terminal review remains separate.

Prospective supervisor v2 requests Task `--exit-code` **only for the source
child**, which passes through the leaf helper's actual exit 2. Native parent,
monitor, shared Child class, source helper and firmware are unchanged. A real
locked Nix Task fixture reproduces default 201 versus passthrough 2. The v2
receipt records its version, explicit passthrough and actual source Task code.
It never normalizes a generic 201 into an accepted diagnostic. Full typed
source/ACK/termination/cleanup validation remains necessary even after exit 2.
See [Task's documented passthrough flag](https://taskfile.dev/docs/reference/cli#x-exit-code).
Root must explicitly launch a fresh 002 after review; the failed 001 caller
does not automatically retry, resume or fall back.

V2 was held before a physical run because startup overhead could exhaust the
fixed schedule. In run 001 the first source's Task start to configuration took
8.579 seconds. The ideal minimum schedule already uses 65 seconds: initial
10 OFF, six requested five-second source periods and five five-second OFF gaps.
That leaves ten seconds for all startup/configuration/cleanup within the
READY +75 source-closure limit. Host-only warmed image loads took about
1.17..1.22 seconds each and harmless help containers about 0.52..0.57 seconds;
help exits before image resolution and is not a measured real source startup.
These measurements justify removing repeated image loads, without extending
the source limit, shortening conditions or promising the resulting schedule fits.

Prospective supervisor **v3** hashes and loads the exact Nix source archive once
**before starting the native parent**. It reads bounded Docker-save manifest and
configuration metadata without extraction, requires the archive's exact tag,
derives expected immutable image ID from configuration SHA256, and requires the
loaded tag's inspected image ID to match. It records archive size/hash, tag,
configuration digest, expected/selected IDs, match result and preload host
brackets. This excludes trusting an unrelated stale tag after a load.
[Docker's image specification](https://github.com/moby/docker-image-spec/blob/main/spec.md#terminology)
defines image ID through the configuration digest.

Each source child alone receives `BLE_SOURCE_PRELOADED_IMAGE_ID` through its
command environment and retains Task `--exit-code`. The source wrapper validates
strict `sha256:` ID format and currently inspected tag identity **before every
source**, never reloading or falling back after an explicit preload request.
It launches by immutable ID and records `image_id` plus
`preloaded_image_reused=true` in its closure receipt. Both fields must match
the preloaded proof before another episode starts. Without the optional preload
environment variable, standalone wrapper behavior still loads the archive.
Native, monitor, common Child, HCI source code, receiver and allowlist remain
unchanged. Six real host-only reuse resolutions totaled 0.151 seconds; source
launch/HCI timing still needs the fresh physical comparison. No successful
six-episode timing or RF/count result is inferred from host-only checks.

## Fixed comparison and actual measurements

Use the unchanged, reviewed native v2 artifact 003: application SHA256
`43875cd929854965e177a02b0b25f22dcac26ddf8390e69ae1f8bf6f593a0e6e`, manifest SHA256
`dc4a96c873d69c9ccc09ff5fba5064b9f07332184565b96eee81cc9dad9f0159`.
The observer runs one passive 90-second scan, filters the exact whole owned AD,
and stops through its actual application cancel/inactive guard. Firmware,
observer parser, original baseline, SDK, roles and SDR allowlist stay unchanged.

The direct source has two conditions: `MaxEvents=255` and `MaxEvents=0`, repeated
in that fixed alternating order three times. Every other source parameter is
fixed: externally reserved handle 1, legacy nonconnectable/nonscannable
properties `0x0010`, primary map 1/channel 37, LE1M, min/max requested interval 20 ms,
duration 5000 ms, exact 16-byte AD `0fffffff4553502d5344522d4556414c`, start delay 0.
Max 0 explicitly passes `--events 0 --unlimited-events`; it is diagnostic only.
No source restart, fallback, changed placement, settings adjustment or retry
repairs a failed episode. Requested 20 ms is not independently measured cadence.

Retain every actual source termination and native owned-report total, including
zeros. For Max 255, accept diagnostic duration termination `0x3c` with an actual
integer count 0..255 and the helper's exact typed mismatch/exit 2 receipt. Also
retain a new actual limit termination `0x43/count255`, exit 0, if observed. For
Max 0, require duration termination `0x3c/count0`, its typed unlimited diagnostic
exit 2 and an explicitly unmeaningful count field. A generic exit 2, timeout,
wrong handle, duplicate termination or unknown JSON record fails the comparison.
An observed positive controller count is new source information; it does not
silently qualify the original 255-event three-trial protocol or an SDR rate.

For each episode require five exact commands and successful command-completion
ACKs: parameters, owned data, enable, own-handle disable and own-handle remove.
The independent sanitized dumpcap monitor must show all 30 commands/30 successful
ACKs and six matching termination status/handle/count records in episode order.
Source `source_closed`, socket-closed, wrapper container removal and natural
process-group quiescence are separate proofs. Missing own-handle cleanup or
container proof blocks the next episode even if the host process vanished;
failure retains `source_cleanup_verified=false`. Group closure alone cannot
prove controller advertising was disabled.

## Readiness, timing and restoration

The sole operator verifies preservation, security, the stable ESP identity,
exclusive UART/HCI ownership and external reservation of advertising handle 1.
Reservation rests on the prior owned disable/remove acknowledgements and
continuous exclusive source ownership; zero active instances alone is insufficient.
BlueZ must already be powered with zero active advertisements before and after;
zero active instances does not enumerate dormant advertising sets. No Bluetooth
controller power, reset, discovery, pairing, global event-mask or address writes
are allowed. Experimental ESP installation, reset and verified restoration are
explicitly authorized through the existing preservation guards.

Start the unchanged native parent; only its validated matching nonce READY
permits the monitor/source schedule. Start the read-only 120-second HCI monitor
and wait for `MONITOR_READY`. Initial source configuration begins after at least
10 actual seconds OFF from native READY. After each naturally closed source
group, wait at least 5 actual seconds OFF before the next source. Every source
group must close by READY +75 seconds; insufficient budget or an overrun fails
closed without shortened episodes. Native END must retain more than 10 actual
seconds after final source-group closure, in addition to the native 90..92-second
completion and aggregate/terminal consistency guards.

On success the 120-second monitor can finish while the native parent performs
its autonomous full-flash restoration: the read-only HCI socket has a separate
boundary from ESP UART. On cancellation or error, close owned source/monitor
groups first, then await the native parent's natural finite completion and
restoration. Never kill the outer native parent or start a competing restore.
If its group remains alive after the bounded wait, leave closure unverified and
prohibit further hardware use. Restoration requires full 4 MiB readback hash and
matching original boot; it does not prove electrical power removal.

Native aggregate intervals retain firmware start/end microseconds and complete
host-line receive brackets. Source configuration/enable/ACK/termination/socket
times and host group-closure brackets are retained too. Phase joins are nominal:
ESP clock rate, controller scheduling and UART/HCI latency are uncalibrated.
Conservatively exclude buckets spanning transition brackets with the existing
one-second guard; publish delivered-report counts and excluded buckets, never
a transmitted-event denominator or detection rate. Native reports may duplicate
across receptions; a null remains inconclusive. A reception difference may
guide investigation but is not a controller-firmware causal diagnosis.

## Private offline supervisor and operator command

The private root files are `.scratch/run_native_direct_reference.py` (v3),
`.scratch/test_native_direct_supervisor.py` and
`.scratch/run_native_direct_reference.task.yml`. Before launching children the
supervisor saves read-only copies and SHA256 of itself, its Task recipe,
reused lifecycle/source/monitor helpers, root Taskfile and flake/lock. Fresh
ignored private directories use 0700/0600; native raw UART/boot bytes remain
private. Sanitized native receipts may be retained publicly; controller
addresses, identifiers, foreign payloads and private paths are excluded.

Hardware-free focused check:

```sh
nix develop .#ci --command task --taskfile .scratch/run_native_direct_reference.task.yml test
```

Prospective command for the sole operator **after review**, using fresh paths:

```sh
nix develop --command task --taskfile .scratch/run_native_direct_reference.task.yml run -- --artifact .scratch/native-reference-artifact-003 --manifest .scratch/native-reference-artifact-003/manifest.json --private .scratch/native-direct-reference-002 --output docs/evidence/native-direct-reference-002
```

The command installs an experimental native observer and restores the verified
original baseline. Its supervisor status reports completion of this diagnostic,
including expected typed source failures; it never marks SDR/count gates passed.

Primary semantics: [Core 6.2 HCI §7.7.65.18 and §7.8.56](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html),
[official legacy event-limit qualification example, p125](https://files.bluetooth.com/wp-content/uploads/dlm_uploads/2025/05/HCI.TS_.p37.pdf),
and [public scan-cancel API](https://mynewt.apache.org/latest/network/ble_hs/ble_gap.html#c.ble_gap_disc_cancel).
Nonzero Max makes actual duration-termination count meaningful; Max 0 requires
count 0. Duration starts at the first advertising event rather than a host ACK.
No observed report count substitutes for an independently measured RF emission
count, and source commands alone do not establish reception.
