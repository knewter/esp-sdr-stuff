# Independent preflight of native direct-source comparison

The [prospective protocol](../../research/native-direct-source-comparison.md)
passes offline preflight for the sole operator's bounded diagnostic. This review
does not record a physical trial or acceptance result. It used no device handles.
Protocol author commit: `837a05b0329d8bec1101e960f8d91ecc6b9aa0d0`.

[Checks and exact hashes](preflight-checks.json) identify the frozen private
supervisor, tests, Task recipe and reused helpers. The reviewer independently
ran the locked Nix CI Task: **22 tests passed**. Prior physical command, ACK,
termination and cleanup layouts supply the fixture. Its prospective option,
container and limit-positive adaptations are explicitly synthetic; tests do not
claim that MaxEvents 0 or a new 0x43/count255 result has been observed.

The unchanged native v2 artifact 003 passes its offline guard in the locked
default shell, and its manifest and all three image parts were independently
rehashed. The experiment alternates MaxEvents 255 and 0 three times, holding the
declared handle, legacy nonconnectable properties, channel, PHY, interval,
duration and owned data fixed. It requires validated native and monitor READY,
initial OFF of at least 10 seconds, inter-episode OFF of at least 5 seconds after
source-group closure, all source groups closed by READY +75 seconds, and an
actual END tail greater than 10 seconds. The existing explicit native cancel,
inactive and 90..92-second completion guards remain required.

Each episode requires five successful command completions and own-handle
disable/remove proof. The independent monitor must match all 30 commands,
30 ACKs and six actual termination records. A typed expected diagnostic exit 2
is distinguished from timeout, transport failure or uncertain cleanup. A new
actual 0x43/count255 branch is retained rather than prejudged. Recursive type
checks reject boolean aliases in numerical fields, including nested cleanup
statuses. Unknown source cleanup remains explicitly false and prevents another
source episode, even when the container and process group have disappeared.

Cancellation regressions show source and monitor cleanup before waiting for the
native parent's natural finite completion and restoration. The outer native
parent is never force-killed, and no competing restoration starts. An unclosed
group remains unverified. Full original-image readback and original boot are
required; these are prospective gates, not newly observed recovery evidence.

The [Bluetooth Core HCI specification](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html)
sections 7.7.65.18 and 7.8.56 support the declared controller-event interpretation:
termination applies to legacy and extended advertising, duration begins with
the first advertising event, and the completed-event field is meaningful with
nonzero MaxEvents but zero otherwise. The official chapter's cached full HTML
was inspected; its hash is retained. The [public scan API](https://mynewt.apache.org/latest/network/ble_hs/ble_gap.html#c.ble_gap_disc_cancel)
also documents successful cancellation and inactive-state semantics used by the
unchanged observer.

Raw UART, flash, source logs and identifiers remain private. Phase joins must
retain whole receipt brackets, nominal firmware intervals and the one-second
guard; clock rate and transport latency are uncalibrated. Native reception
reports may duplicate, and null reception remains inconclusive. No source RF
emission denominator, SDR-positive result, detection rate, Trial B prerequisite
or RF/count acceptance follows from this preflight or from native reports alone.

## Physical run 001: failed comparison, observed cleanup and recovery pass

The [retained first run](../native-direct-reference-001/README.md) **failed**
after one source; five conditions never ran. Initial preflight missed the real
Task/leaf exit boundary: mocked Task exit 2 did not exercise Task's default
command-error exit 201. The first source's actual Task footer identifies leaf
exit 2, while its naturally closed group returned 201. Neither this review nor
later postprocessing converts the failed schedule into a completed comparison.

[Independent physical checks](trial-001-checks.json) reparse all 23,307 saved
UART bytes and match every public typed field, all 90 contiguous buckets and
END. There are 59 cumulative owned reports; application cancel returned zero,
discovery was inactive, and actual firmware elapsed time is 90.087992 seconds.
Independent integer-nanosecond phase reconstruction gives 24 reports in two
guarded ON buckets, zero in 15 initial OFF and 63 final OFF buckets, and 35 in
ten transition buckets. Every public CSV row and the summary agree. These are
nominal guarded associations with uncalibrated clocks and transport latency.

The saved source and independent monitor match all five requested commands and
ACK status zero, including own-handle disable/remove. Actual termination is
0x3c/count0. Socket, container and process groups closed; the interrupted monitor
was reaped and removed. The original orchestration retains
`source_cleanup_verified=false`, because its exit guard failed before validation.
The review separately records observed cleanup verified from saved receipts.
Both full 4 MiB before/after images independently hash to the preserved original,
and private original reset-boot content passes. Controller before/after state
agrees. Native reception of the owned marker despite a zero controller field
does not supply RF emission counts, independent protected-PDU replay or SDR proof.

The actual corrected plot was rendered and inspected. It labels comparison
failure, shades only the first source and retains five unrun conditions. Its
scope footer was initially obscured by the axis label; a separate plot-only fix
reserves space without changing data. Public hashes identify the final reviewed
evidence commit `2f007cdef4ad902e0c414445986e238616cbb9f6`.

## Prospective supervisor v2: exit fix passes; timing holds launch

[Version 2 checks](preflight-v2-checks.json) cover the narrow source-only
`task --exit-code` change. The reviewer independently ran **24 locked Nix Task
tests**, including real hardware-free Task subprocesses: default exit 201 is
rejected, source passthrough returns leaf 2, and missing/generic typed receipts
still fail. Native parent, monitor and common Child commands remain unchanged;
there is no generic 201 normalization. [Task documents both behaviors](https://taskfile.dev/docs/reference/cli#x-exit-code).

Fresh run 002 is **held for startup-budget review**. Actual run 001 took
8.579117 seconds from source Task launch to configuration. The fixed six-source
and OFF schedule needs 65 seconds before startup/cleanup overhead, leaving only
10 seconds before READY +75. Root's hardware-free measurements found warmed
image loads around 1.17–1.22 seconds and capability-free help launches around
0.52–0.57 seconds each. Repeating those costs risks overrunning the fixed bound.
A separately reviewed immutable preload/reuse path may address that cost; this
receipt does not approve longer bounds, shorter conditions or an automatic retry.

## Prospective supervisor v3: guarded preload permits a bounded fresh trial

[Version 3 checks](preflight-v3-checks.json) pass offline preflight. The reviewer
independently ran **30 private supervisor and 14 public wrapper tests** with
locked Nix dependencies. The final protocol is committed at `af8a09f`, byte-equal
to author `85372a9`; the exact caller, wrapper, tests and Task hashes are recorded.
The failed first comparison and its original false caller cleanup flag remain
unchanged. Its independently observed controller cleanup and full restoration
were already verified before this prospective decision.

The caller hashes and loads the exact Nix archive once before starting the native
parent. Independent archive inspection matches the caller's bounded streaming
metadata parser: 90,619,442 archive bytes, SHA256 `0263ef47…`, exact single tag
and 6,357 configuration bytes with SHA256 `699e00a1…`. This configuration digest
defines the immutable image ID, as documented by the
[OCI image configuration specification](https://github.com/opencontainers/image-spec/blob/main/config.md).
The actual host-only preload receipt resolves the loaded tag to that same ID;
it took 1.852 seconds outside the native observation. Malformed metadata, a
wrong tag or mismatched configuration/image ID fails before the native child.

Only source children receive the explicit preloaded ID and Task exit passthrough.
Every episode rechecks the tag, launches by immutable ID and requires the same
ID plus `preloaded_image_reused=true` in its closure receipt. An explicit mismatch
has no reload or fallback. Typed command acknowledgements, termination, owned
disable/remove, socket/container release and natural whole-group closure remain
required before the next source. Native, monitor and common child commands stay
unchanged; the native parent is never force-killed or given a competing restore.

The three [public host timing receipts](../native-direct-startup-budget/README.md)
are byte-equal to their private and committed versions. Six calls to the actual
reuse branch totaled 0.151470 seconds without image loads; the help path is
explicitly separate. This removes a measured repeated load cost and permits
a sole-operator fresh bounded run 002. It **does not guarantee** real HCI startup,
cleanup or completion of the six-episode schedule. Initial and intervening OFF,
READY +75 source closure, native 90..92-second stop and greater-than-ten-second
actual tail remain unchanged and fail closed on an overrun. No episode may be
shortened or replaced. This review opens no device handles and establishes no
physical comparison, RF emission denominator, SDR positive, Trial B prerequisite
or RF/count acceptance.

## Physical run 002: six conditions, native reception and recovery verified

The [completed second comparison](../native-direct-reference-002/README.md)
passes independent offline review. [Exact physical checks](trial-002-checks.json)
identify the reviewed evidence revision `3d00063`, frozen v3 caller, private
input hashes and all 11 public file hashes. Every public byte matches the
committed evidence. The reviewer rehashed the unchanged artifact 003 manifest
and all three image parts, matched the actual installation's data-verification
log, and checked the executed-file snapshots. No device handles were opened.

All **23,457 saved UART bytes** hash correctly and reproduce CONFIG, fresh
READY, 89 aggregates and END. Every public typed field, contiguous interval,
cumulative count and RSSI summary agrees. The observer reports **363 owned
receptions**, actual application cancel zero, inactive discovery and firmware
elapsed time **90.092890 seconds**. This JSON stream has no independent
transport CRC or protected-PDU replay.

The six fixed alternating MaxEvents 255/0 sources match the separate monitor:
30 exact commands, 30 successful acknowledgements and six actual **0x3c/count0**
terminations. Each source's typed diagnostic exit is 2 through Task passthrough.
Own-handle disable/remove succeeds, sockets and containers close, and whole
process groups end naturally. Every source verifies the same preloaded immutable
image. The wrapper's controller-cleanup field remains unconditionally false;
the supervisor separately validates HCI cleanup before the next episode.

Initial OFF lasts 10.561524 seconds. Every intervening OFF meets five seconds,
all source groups close by READY +70.572797 seconds, and actual END leaves
19.538806 seconds after the last source-group closure. Integer-nanosecond joins
using complete READY brackets, whole firmware intervals and one-second guards
match every phase CSV row and summary: **124 reports in 11 guarded ON buckets**,
**zero in 36 guarded OFF buckets**, and **239 in 43 retained transition buckets**.
Every source episode has positive guarded reception. Unequal included intervals,
possible duplicate reports and uncalibrated clocks/controller/HCI/UART latency
prevent an emission rate or equivalent-emission comparison.

Both full **4 MiB** before/after images independently match the preserved
original SHA256 `6e8f0793…`; private boot content matches the original application,
SDK and both GPIO states. The native UART worker and all child groups close,
controller before/after state agrees, and restoration verifies. This is reset
boot recovery, not another electrical power-cycle observation. Raw UART, flash,
boot and source logs stay private with mode 0600; public files expose no unique
addresses, bridge identifier or absolute host paths.

The actual SVG was rendered and inspected. It retains all buckets and six
source shades, labels nominal timing and states that reports are not emissions.
The result establishes native receivability of the owned marker under both
limit settings while the controller field is zero. MaxEvents 0 makes that field
unmeaningful; the MaxEvents 255 zeros supply no usable emitted denominator.
This does not diagnose a controller cause, establish hidden-SDR reception,
satisfy conditional Trial B, or close RF/count gates. Failed run 001 remains
separate with five unrun conditions.
