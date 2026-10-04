# Extended primary-header preparation (UNVERIFIED RF)

Profile `extended-primary-zero-data-v1` asks whether a bounded, counted
extended source exposes a complete, independently attributable primary header
to the ESP snapshot receiver. This prospective diagnostic preserves all
[original counted-trial gates](ble-counted-trials.md), the original legacy
Trial B prerequisite, previous failures and auxiliary-data results. No hardware
acceptance or OpenSpec checkbox follows from these host tools.

## Fixed source profile and operator boundary

One root operator reserves free handle1 on hci0, verifies powered state and
BlueZ ActiveInstances0, and retains its private stable controller binding.
No reset, event-mask overwrite, scan, pairing or power/discovery change is
required. The source sends only parameters2036, complete data2037, enable2039,
scoped disable2039 and scoped remove203c. Repeated/cancelled trials require
observed cleanup and closure before any later episode.

The new explicit flag requires extended mode, handle1, interval20ms,
MaxEvents100 and duration5000ms. Legacy defaults still carry the unchanged
16-byte manufacturer AD. New wire parameters are properties0x0000,
primary-map0x01 (channel37), public Own_Address_Type0, primary/secondary PHY1,
secondary-skip0, SID0, filter-policy0 and scan-request-notification0. Data is
`01 03 01 00`: handle1, complete operation, fragmentation preference1,
zero advertising-data length. Enable is `01 01 01 f4 01 64`:
500 ten-ms units and maximum100. No fallback/restart is permitted.

Root-only source command after immutable source/container/image and monitor
freeze:

```sh
nix develop --command task source:ble-direct:container -- \
  --handle 1 --interval-ms 20 --events 100 --duration-ms 5000 \
  --start-delay 0 --extended-mode-diagnostic --primary-zero-data-diagnostic
```

Retain actual parameter/data/enable command acknowledgements, exactly one
matching handle1 termination with status0x43/count100 in both native source
and complete independent monitor, all cleanup acknowledgements0, source
socket/container closure, normal monitor completion and unchanged postflight.
Wrong/missing/duplicate/timer0x3c termination fails the maximum-count profile;
retain every failed attempt. Controller-selected transmit power is recorded,
not treated as calibrated field strength. Count units follow
[HCI Vol4E7.7.65.18 and7.8.56](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html).

## Primary ownership and decoder

Zero host data does not force auxiliary omission. The controller chooses
whether to use AUX and where to place AdvA. Without AUX, this undirected
nonconnectable/nonscannable primary must carry AdvA; with AUX, primary AdvA
may be absent. Primary AD data is excluded. See
[Core5.4 Vol6B Table2.4,2.3.4 and4.4.2.6](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-54/out/en/low-energy-controller/link-layer-specification.html).

The operator freezes a mode0600 reference inside a mode0700 ignored directory
before acquisition: JSON fields `schema:1`, `address_type:0`,
`advertising_sid:0`, `adva_lsb_first_hex` containing the six private public
address bytes in transmitted octet order. Obtain that owned address through
the existing private controller identity receipt; do not infer it from the
waveform, publish it or pass it on the command line. Freeze the binding hash
privately with provenance. Address matching alone is attribution under these
exclusive-source controls, not cryptographic authentication against spoofing.

[The offline tool](../../tools/ble_extended_primary.py) requires type7, full
24-bit PDU CRC and strict extended-header lengths/flags/field bounds. It
rejects reserved fields, AdvMode other than0, TargetA, CTEInfo, SyncInfo, ACAD,
AdvData and mismatched ADI/AuxPtr combinations. Ownership additionally needs
present, exact private public AdvA and SID0 if ADI exists. Missing AdvA,
ADI-only identification, random-address type, a foreign address and auxiliary
AD cannot supply ownership. DID, AuxPtr bytes and optional power are
controller-selected, not trained or declared independently known payload.
A with-AUX result verifies the known address/header subset; it is not a claim
that every varying header byte was known independently. AUX is not followed.

The legacy decoder source remains byte-for-byte SHA256
`834fdd78e3221d0625eaa7cf1059b9bd59d3b8b9fa929578f2555bff64130128`.
The new tool clones its receiver code objects with a private parser callback,
leaving legacy globals unchanged. Coarse period4, AA correlation>0.78,
AA errors<=2 and bounded refinement13 periods3.97..4.03 ×17 offsets±2 ×37
biases−0.45..0.45 remain unchanged. Public AA alone trains each hypothesis;
full CRC validates slicing, and AA correlation selects results without using private
ownership outcomes. No payload repairs or post-outcome search expansion.

## Future receiver qualification and accounting limits

Freeze source, decoder, receiver image/settings, coordinator, Nix lock/closures,
private bindings and placement before data. Install only after verified full
preservation; root owns ESP, source and restoration. A future fixed profile
must name LO/BW/gain/rate/bits, whole request-response timestamps and all
transport SHA/CRC/count checks. No receiver profile is qualified by this
preparation. The no-AUX primary is144µs (152µs with power); an address-bearing
AUX pointer header is184µs (192µs with power). Each fits nominal16MS/s
1.02375ms windows; physical timing/clock and full waveform bounds still need
proof. The longest also nominally fits80MS/s204.75µs, with little edge margin.

Before interpreting source responses, preserve >=5s initial OFF baseline,
three predeclared repetitions, >=1s source-OFF gaps and >10s continuous
post-cleanup receiver tail. Monitor must be ready before receiver through all
cleanup. A positive requires full nominal preamble-through-CRC inside the
waveform and whole acquisition bracket inside enable-ACK+100ms through
termination−100ms, matching source and monitor profile. Retain OFF/boundary,
zero-hit and failed trials. Deduplicate slicing hypotheses; two distinct
owned clusters in one <=1.024ms window contradict this20ms source profile and
remain unresolved, including during OFF/boundaries. CLI outputs are candidate
diagnostics, not an event-rate numerator or source association report.

The controller count is completed extended advertising events, not an
independent count of air packets. Map37-only permits at most one primary PDU
per event; PDUs or entire events can be omitted for other functionality.
Therefore count100 alone cannot certify100 radiated primary frames. See
[Core6.2 Vol6B4.4.2.1/4.4.2.2](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/low-energy-controller/link-layer-specification.html).
The original >=100 deliberately emitted-event decision remains open until
count-to-primary applicability is justified and known complete payload proof
is physically recorded. Source-event-normalized reception may be reported
only with its precise units and assumptions. N−verified-full-hits means
unverified complete reception, with acquisition gaps, truncation, source
omission, interference and decoder uncertainty unresolved; it is not confirmed
RF misses. Null snapshots remain inconclusive. No auxiliary AD is silently
relabelled as the primary known marker.

## Host validation and offline invocation

From the worktree, an owned private Taskfile `.scratch/ble-primary-task.yml`
wraps tests and decoder commands; it changes no shared Taskfile/flake. Host
checks use the locked environment and open no device/container:

```sh
nix develop .#ci --command task -t .scratch/ble-primary-task.yml test
nix develop .#ci --command task -t .scratch/ble-primary-task.yml decode -- \
  --input PRIVATE/iq --output PRIVATE/primary-decoder.json \
  --owned-reference PRIVATE/owned-primary-reference.json \
  --rate 16000000 --bits 8 --samples 16380 --frequency-translation-hz -1000000
```

Equivalent decoder invocation within Nix is
`python3 tools/ble_extended_primary.py` with the same arguments. The independent
reflected CRC/register whitening fixture matches the published
[Core6.3 Vol6C4.2.1 sample](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core_v6.3/out/en/low-energy-controller/sample-data.html).
The 88 scoped host regressions pass. All primary-header and modulation
fixtures are synthetic host proof, not
RF evidence. Original legacy decoder/source/container regressions also run.
