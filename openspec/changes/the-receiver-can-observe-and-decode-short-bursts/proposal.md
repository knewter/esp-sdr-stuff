## Why

Seeing activity is useful but does not establish packet decoding or reliable event detection. We need an honest application shortlist based on finite capture windows.

## What Changes

- Evaluate channel occupancy and repeated-burst detection on an owned controlled source.
- Try offline demodulation of complete short bursts that fit captured windows.
- Report hit rate, decode rate and missed windows separately from spectrum visibility.

## Capabilities

### New Capabilities

- `radio/burst-applications`: Decide which interference, educational DSP and short-burst applications are useful on this board.

### Modified Capabilities

None. Existing identity records remain factual baselines.

## Impact

Physical ESP32 and owned repeatable Wi-Fi/BLE or simple 2.4 GHz test waveform. Protocol-generator hardware depends on inventory.

Dependencies: [the board captures repeatable radio snapshots](../archive/2026-10-01-the-board-captures-repeatable-radio-snapshots/proposal.md), [the spectrum reveals controlled 24ghz signals](../the-spectrum-reveals-controlled-24ghz-signals/proposal.md)

## Non-goals

No whole-session Bluetooth capture, guaranteed packet logging, continuous audio or encrypted-content access.

## Decision gate

At least 100 deliberately emitted repeat events with ground-truth counts and capture hit rate; a decoding claim includes a complete waveform and verified payload.

## Evidence and sources

Baseline: [research](docs/research/source-index.md). Sources: [primary-source register](docs/research/source-index.md).

## Separate longer primary opportunity diagnostic

The [fixed receiver001 review](docs/evidence/ble-primary-zero-data-receiver-001-review/README.md)
retains365 snapshots but only11 whole guarded ON windows across about7.4 seconds
of source enable time. Its null remains inconclusive. The separately prospective
[timed-v2 protocol](docs/research/ble-primary-timed-zero-data-v2-protocol.md)
plans three25-second zero-data extended source episodes at the unchanged
ten-bit/BW20/manual48 receiver settings, placement and blind decoder bounds.
This is a diagnostic opportunity extension: a coverage gate of at least100
whole guarded ON windows altogether and25 per repetition counts acquisition
windows, never emissions. Original decision gates above remain unchanged.

Dependencies are a new explicitly selected native timer profile and immutable
Nix source archive, independent host preflight, actual source-only timer-profile
qualification, a separate receiver caller/holder freeze, complete preservation
and root-only operation. Existing v1 source/image/guards/private inputs remain
unchanged. No added RF equipment or FPGA wiring is needed for this diagnostic;
calibrated RF/air-count conclusions remain outside its scope. Failure or sparse
coverage retains the attempt and admits no automatic retry or acceptance task.

## Bounded source004 preparation prerequisite

[Actual source003 cost evidence](docs/evidence/ble-primary-timed-startup-preparation-review/README.md)
retains a31.198-second frontwork refusal and37.115-second full verification,
not operational fit. A NEW source004 bundle and outer gate will perform
hermetic pinned selection before monitor under the existing165/300-second
clocks, then every fresh local input, runtime, NAR and archive check inside45.
Exact locked public input retrieval is allowed only during selection; this is
not a globally network-denied host. Bounded parallel verification must retain
complete ownership and whole-proof equality. See [design](design.md#source004-bounded-verification-prerequisite).
Implementation, actual current-provider/timing proof and independent review
precede task4.3 operation; all source003 failures, hardware gates and wire
profiles remain unchanged. No source attempt follows automatically.

## Source004 verification cost evaluation (UNVERIFIED)

The [accepted historical read-only preparation](docs/evidence/ble-primary-timed-source004-readonly-review/README.md)
completes whole proof but does not fit source admission. Saved-ledger research
measures75.134333 seconds for the verifier and30.320421 seconds for its concurrent
content span. Both exceed the13 seconds available before the unchanged native32
floor on source45, even before other source frontwork. Their causes remain
unmeasured. Add bounded cost records in a NEW immutable evaluation bundle first;
select a later optimization only from complete measured attribution and a
separately reviewed plan. Git batching, shared fresh process censuses and reduced
redundant archive/tool reads are hypotheses, not speedup or admission claims.

This refines the existing `radio/burst-applications` preparation dependency;
it adds no radio capability, equipment, wire change or accepted requirement.
The host owns measurement; the original ESP32 remains the receiver. Preserve
the reviewed corrected source004003 ownership baseline and every original
fresh-content, cleanup and clock gate. The measurable software gate is an
independently reviewed cost record with reconciled operation counts and clock
scopes, followed by sole-root fresh complete current-tuple timing with room for
all frontwork and native32. A faster partial or compatible proof cannot satisfy
it. Controller qualification and receiver action remain separate unchecked gates.
