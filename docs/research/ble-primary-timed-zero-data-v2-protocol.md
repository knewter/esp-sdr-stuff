# Prospective longer zero-data primary diagnostic v2

Declared October 4, 2026, from clean source `12138abb`, before implementation,
packaging or any new source/receiver action. This is a separate timed diagnostic,
not a revision of `extended-primary-zero-data-v1` or its qualified count100 gate.
It preserves the original emitted-event requirements, original eight-bit/BW12/
hardware-gain Trial B, all earlier outcomes and accepted specifications.

## Why this condition is useful

The [independently reviewed fixed receiver001](../evidence/ble-primary-zero-data-receiver-001-review/README.md)
preserves 365 ten-bit snapshots but only 3/4/4 whole guarded ON brackets across
three source episodes lasting about 7.4073 seconds altogether. Its zero primary
decode result remains inconclusive. This condition increases source-enabled
opportunity while holding the receiver, placement, ownership/parser and blind
decoder fixed. It does not increase snapshot duty factor or guarantee a primary
PDU, present AdvA, a capture, a decode or a repeated RF response.

Requested source enable duration is 3 x 25 seconds. At the historical average
365/180.009958295 snapshots per second, roughly 150 snapshots could fall in that
time before whole-bracket and 100 ms guards. This is an opportunity estimate,
not a prediction based on a known air schedule. The receiver coverage gate is
at least 100 whole guarded ON brackets altogether and at least 25 in each
repetition, explicitly counted as acquisition windows, never emitted events.
If the condition supplies fewer, retain every attempt and label opportunity
insufficient; do not repeat or relabel the original null.

## Exact separately versioned source

Profile name: `extended-primary-zero-data-timed-v2`.

| Field | Fixed request |
| --- | --- |
| Controller and handle | Privately identity-selected hci0, reserved free handle1 |
| Properties / primary map | 0x0000, 0x01 (channel37 only) |
| Min/max interval | 32 x 625 us = 20 ms |
| Own/unused peer address types | 0 / 0, unused peer address zero |
| Filter / power request | 0 / 0x7f; actual signed selected power recorded |
| Primary/secondary PHY | 1 / 1, secondary skip0 |
| SID / scan-request notification | 0 / 0 |
| Advertising data | Complete operation3, fragmentation preference1, length0 |
| Max_Extended_Advertising_Events | 0: no count limiter |
| Duration | 2500 ten-ms units = 25000 ms |
| Start delay | 0 |

Enable2039 payload is exactly `01 01 01 c4 09 00`; complete empty data2037 is
`01 03 01 00`. Cleanup disable2039 is exactly `00 01 01 00 00 00`, followed by
scoped remove203c payload `01`. Send only the same five commands as v1:
parameters2036, data2037, enable2039, scoped disable2039 and remove203c.
No fallback, restart, reset, event-mask, power/discovery, scan or pairing change.
Do not choose a different interval, handle, duration, event limit or AD on failure.

[Bluetooth Core HCI 7.8.56 and 7.7.65.18](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html)
define a finite duration in 10 ms units and timer termination status0x3c. Duration
starts with the first advertising event, not the host ACK; the timer gives no
independent air count. The returned completed-count byte must be retained and
type-checked as UINT8 in both readers, with exact reader agreement. Do not assume
zero, infer a count from elapsed time/interval, or reject another UINT8 solely
to manufacture a denominator. `controller_completed_count_verified` and
`termination_count_field_meaningful` remain false, and every air count/rate is null.
The specification expects zero when MaxEvents is zero; any nonzero observed
byte is an explicitly retained conformance anomaly, not a usable count. The
timed diagnostic qualification criterion tests the timer/profile/closure and
reader agreement, rather than silently substituting the specification's zero.

New success status is `controller_timed_profile_verified`, distinct from v1's
`controller_count_verified`. Success requires the exact requested full wire
profile in independent monitor records, five ordered ACK0 pairs, matching native
records, valid signed2036 selected-power response in [-127,20], exactly one
handle1 timer0x3c termination after accepted enable, and complete scoped cleanup.
Observe at least 24.0 seconds and less than 30.0 seconds from native enable ACK
to native termination; independent monitor timestamps must support the same
conservative interval and ordering. These host-time bounds reject a materially
short/late episode; they do not calibrate the RF timer or claim exactly25 seconds
on air. Preserve actual native and monitor clocks and all count/power fields.
Missing, premature, duplicate, mismatched, out-of-order or0x43 termination fails.

## Native constraints and implementation boundary

At the declared base, `tools/ble_direct_hci_source.py` cannot run this profile:
`validate_mode_diagnostic` fixes duration5000/count100-or255/bounded events,
`validate_primary_zero_data` additionally fixes count100, `duration_units` caps
5000 ms, and `Source.run` explicitly refuses unlimited-event counted success.
`tools/ble_source_container.py` calls these same guards before Docker. Passing
different command-line arguments or teaching the old caller to accept0x3c would
weaken historical proof and is excluded.

Implement a separate `tools/ble_primary_timed_source.py` with strict fixed-v2
validation, separate duration/enable construction and a separate timed runner.
Reuse the unchanged v1 parameter/data/frame/event parsing and bounded command
primitives through ordinary imports/composition or a local subclass. Never
replace v1 globals, `Source.run`, validators, success status or cleanup policy.
Keep the old native file, old container helper, legacy data and old monitor/
decoder bytes unchanged. The new runner must preserve cancellation, native
ACK/event ordering, duplicate detection and always attempt bounded scoped
cleanup once parameters may have reached the controller. Native command ACKs
remain capped2 seconds each; timer wait is capped30 seconds after enable ACK;
normal completion includes log/descriptor and owned whole-process-group closure.

Add a separate `tools/ble_primary_timed_container.py`, immutable image selection
and a new optional Nix package `ble-primary-timed-source-image`. The archive
contains the new native entrypoint and the exact unchanged old module it imports,
plus the locked Python runtime. Name/tag must differ from the Python-only v1
archive, with the v2 tag derived from its source-bearing derivation. Execute
the archive-resident entrypoint; do not silently reuse a v1 mounted script,
mutable image tag, source override or pull fallback. Keep the old image
derivation/tag/archive contents unchanged and prove that comparison offline.
Adding flake/Task inputs still changes current production source tuples, so all
affected root freezes must refresh after merge. The strict Forgix19-source
artifact guard then requires a new root ARM artifact if a later register trial
is pursued; do not alter the guard or historical artifact receipt.

New public Task entrypoints select the v2 native/container/test/package operations
explicitly. Existing v1 tasks and defaults remain unchanged. No dependency is
installed outside the locked flake. Building/loading the new archive is a later
sole-root operation after source review; this plan performs neither.

## Two separate physical gates

First freeze and independently review host code/profile/closure proof, then the
root operator performs exactly one bounded source-only qualification. Use a new
private directory, current controller/endpoint/loaded-image admission, inherited
global flock and exact process/container/CID/active identity receipts. The monitor
must be ready before source and remain complete through cleanup. Suggested fixed
source-only monitor duration60 seconds, readiness15, grace5 (active bound80),
outer readiness75, source episode45 and whole supervisor165, all anchored before
their requested operations. The source must naturally close before monitor end.
Strict fresh clock/liveness checks apply before and after every intent, admission,
spawn, helper return, closure and durable qualification. No automatic retry.
Qualification binds the exact v2 wire profile, actual observed timer0x3c,
count metadata, elapsed bounds, source/archive/runtime/transitive helper bytes
and normal closure. A v1 count100 receipt cannot qualify this timer profile.

Only after independent whole saved qualification review may a separately frozen
receiver condition run. Copy/adapt to a NEW ignored private caller/support/
dispatch/account/test/Task directory and a NEW outer-holder directory, with a
v2 qualification schema and exact independent receipt. Keep all old15 receiver
inputs, old holder and old receipts byte-exact. Do not monkeypatch old module
globals or substitute a v2 result beneath old version labels. Reuse unchanged
radio/preservation helpers coherently and freeze their actual transitive imports.
The v2 dispatch selects the new source image/helper and records actual command,
image/name/CID, active running witness, PID/PGID/start identity and natural group
absence. Whole monitor/native profile verification must reject v1/v2 mixing.

## Receiver and complete schedule budget

Receiver is the same verified UART921600 artifact with ten signed bits/component,
nominal16MSPS,16380 pairs, LO2401 MHz, BW20 MHz and manual48, exact setting ACKs,
existing placement and private AdvA binding. Preserve two complete4MiB originals,
fresh pre-install readback, guarded install, verified application, full restore/
readback and original reset boot. Retain every complete raw row and failure
prefix. One continuous180-second receiver contains exactly three ON/OFF pairs;
no separate or spliced tail repairs the condition.

| Boundary | Fixed cap / requirement |
| --- | --- |
| Monitor launch-through-ready | 75 seconds, anchored before spawn |
| Monitor producer | readiness15 + capture240 + grace5; active total260 |
| Receiver launch-through-ready | 30 seconds; also before monitor admission end |
| Initial baseline hold | 10 seconds; actual OFF at least5 seconds |
| Each complete source episode | 45 seconds, including all per-repeat work |
| Two inter-episode OFF holds | 2 seconds each; actual OFF at least1 second |
| Latest source3 whole-group closure | strictly before receiver-ready+165 seconds |
| Final continuous OFF hold | 10.1 seconds, last complete payload strictly >10 seconds after closure |
| Receiver natural finish | before receiver-ready+195 seconds |
| Monitor natural finish | before monitor-ready+275 seconds |
| Whole acquisition supervisor | 420 seconds, anchored before monitor spawn |

For each repetition anchor the45-second limit BEFORE its controller preflight,
complete freeze/runtime/image admission, intent persistence, inherited-lock
recheck, spawn, normal termination, exact container/group absence and durable
episode receipt. Use the minimum of that immutable limit, latest source closure,
monitor admission and acquisition supervisor at every operation. Never start
the45-second clock after preflight or renew it after delay. Existing per-helper
timeout60/15 values cannot outlive this parent budget; dispatch/wait their
remaining cap or refuse before access. Reserve cleanup time and retain a
conservative failure/quarantine when natural closure cannot be proved. Native
command/wait ceilings may not all be consumed within45 seconds; this is a
success ceiling, not a promise to tolerate every operation's maximum delay.

Budget with these inclusive source episodes is10 + 3x45 + 2x2 + 10.1 =159.1
seconds from receiver ready, leaving20.9 seconds within180 for scheduling slack.
Observed v1 freeze overhead of roughly7 seconds per repetition is included in
the45 seconds, not added afterward. Charge all post-episode verification and
clock reads to the episode before its OFF hold. Abort new sources if any cap,
coverage/integrity/profile or liveness gate fails; preserve unexecuted intents.
Whole acquisition420, monitor240/260/275 and normal finish bounds stay fixed.
Preservation/install/restore operations keep their existing bounded600-second
owned policy; the new holder preserves5400 whole-caller/1800 first-cancellation
cleanup ceilings, inherited direct-Python FD launch, truthful durable terminal
and separate conservative lock keeper. Unknown UART/crash ownership continues
to quarantine, never automatic flash/recovery/release.

## Offline proof and result limits

Before physical admission require locked Task tests for exact full wire/UINT8
fields, v1 rejection preservation, distinct statuses/archives, ACK failure/
power shapes, timer/event disagreement, pre-enable/duplicate termination,
early/late timers, cancellation and scoped cleanup; saved monitor pcap chunk/
redaction behavior stays unchanged. Actual harmless process/flock tests must
cover slow preflight, freeze, fsync, spawn, lock and post-closure operations,
equality to all clocks, descendants, current endpoint/image substitutions,
holder cancellation/quarantine and final persistence. Verify whole source/
private/import/runtime/Nix reference closure and actual archive bytes/entrypoint
before independent preflight. No code/build/device/container action belongs to
this planning checkpoint.

Offline replay every saved receiver waveform with unchanged decoder bounds,
translation-1MHz and full private payload SHA/CRC/count integrity first. Require
full protected type7 primary/CRC, present exact private public AdvA and SID0 when
present, and whole acquisition bracket within enableACK+100ms through actual
termination-100ms. Missing AdvA, auxiliary AD, ADI-only, foreign and boundary
results are not source ownership. Count distinct owned clusters conservatively;
multiple owned clusters per snapshot remain unresolved. Retain all OFF/null/
boundary observations, count actual guarded coverage per repetition, and
independently review the entire saved lifecycle/restoration/source/waveform join.

No event-normalized rate, independently counted primary emission, sensitivity,
miss rate, reliable logger or three reciprocal responses follows from scheduled
25-second sources. A full CRC/address primary positive is the same narrow
ownership/header evidence as before; varying header bytes are not an
independently known complete payload. No diagnostic success checks original
tasks1.1/1.2, relaxes Trial B, rewrites365null evidence or archives experiments.
