# Observe the forced-selector readback across an IQ dump

This document declares the separate diagnostic design. Its first completed
[physical run](../evidence/receiver-register-observation-002/README.md) and
[independent review](../evidence/register-observation-independent-review/README.md)
record 20 valid snapshots and 81 sampled stages with full original restoration.
Those results support sampled field consistency only. The RF/count acceptance
gates and interpretation limits below remain unchanged.

## The smallest new observation

Read `(RX_GAIN >> 24) & 127` at declared acquisition stages. Call it
**forced-selector field readback**, because the pinned receiver writes this
field when applying a manual selector. Do not call it live AGC gain, effective
analog gain or calibrated dB. The companion observation remains bit23.

The [completed gain diagnostic](../evidence/gain-state-diagnostic-001/README.md)
observed software MANUAL/48 and bit23=1 at all 41 queries around 20 valid
snapshots. It did not read the upper selector field or observe either field
inside acquisition. The fresh [8-bit control](../evidence/ble-bluez-control-001/README.md)
and [10-bit control](../evidence/ble-bluez-control-002/README.md) together retained
2,248 transport-valid waveforms with no accepted complete owned BLE packet.
The [five historical packets](../evidence/ble-controls-decoding/README.md) remain
separate positive evidence. Native BLE reception establishes a different
receive path; it does not resolve these SDR nulls or qualify Trial B.

## What the pinned source establishes

This analysis uses receiver revision
`550fadea4d00a9e26ce921c5832167becb3dc20c` and SDK revision
`25fe69f946311abdaf9ad56591f25fedbc20ac98`.

| Source boundary | Observation supported by the code |
| --- | --- |
| [RX_GAIN definition](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L34) and [apply_gain](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L158-L162) | At address `0x3ff5c02c`, manual mode writes the cached selector shifted by 24 and sets bit23; hardware mode only clears bit23. |
| [GAIN?](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L212-L220) | Mode/index are cached software state. The final reply field reads bit23. FREQ retunes, prepares RX and reapplies cached gain. |
| [acquire_iq](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L82-L119) | Acquisition temporarily changes the filter, dump controls, SRAM ownership and byte selection, then restores them. It contains no apply_gain call. |
| [capture](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L131-L155) | Packing, CRC32 and DATA/payload transmission follow acquisition and restoration. |
| [initialization](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L234-L253) | gain_max is sampled once from bits8–14 at startup; this is not a post-retune live-index readback. |

Those statements describe firmware operations. They do not establish the
hardware's effective gain semantics or exclude changes made by the PHY/ROM.
The proposed upper-field interpretation is limited to readback of the field
the firmware writes. A stale manual field in hardware-AGC mode would not prove
that hardware AGC uses that selector.

## Proposed finite observation

Preserve the existing diagnostic's fixed profile: LO 2401 MHz, requested
filter 20 MHz, MANUAL selector 48, nominal 16 MS/s, ten-bit components and
16,380 pairs. Apply settings once, then acquire exactly 20 snapshots within an
absolute 30-second ceiling that includes initial settings and queries. Keep
placement as found. Operate no Bluetooth source in this minimal register
diagnostic. No setting reapplication, retune, retry, resynchronization or
automatic repair is permitted in the acquisition loop.

Keep one initial post-settings record and four small RAM records per capture:

| Stage | Proposed location and meaning |
| --- | --- |
| `post_settings` | After the one successful MANUAL/48 application, before the first capture. |
| `before_acquire` | At acquisition entry before changing dump controls or applying the temporary filter. |
| `armed_before_trigger` | After filter/dump configuration, before the trigger and existing capture-duration start point. |
| `dump_complete` | After reading completion/status and calculating existing elapsed time, before clearing the dump controls. A timeout records the failed completion state instead. |
| `restored_after_dump` | After restoring SRAM ownership, byte selection and filter, before validation, packing or UART output. |

Each record carries a fixed schema version, capture ordinal, stage, nominal
firmware read bracket, forced-selector readback, bit23 and raw measured
hook-body CPU cycles with explicit measurement overhead and wrap limits.
Preserve the existing
completion/count/elapsed metadata to join records to their payload. A complete
20-capture run has 81 stage records. Failure retains the actual prefix and
does not manufacture missing stages.

The record array must have a compile-time bound and reside outside the fixed
MAC-dump sample slab. Review the linker map for that separation. Reads and
timestamp collection can perturb timing; measure their acquisition overhead
and report it rather than assuming observation is free. The new artifact
changes instrumentation, so this is not a comparison changing only RF settings.

Do not print, hash, allocate, persist or issue UART queries in the active dump
interval. Extract the allowlisted fields into RAM. After dump cleanup and a
complete DATA header plus its exact binary payload, send a bounded typed
diagnostic receipt for that capture. Define this response extension under a
distinct diagnostic protocol/version; existing CAP20 consumers must not
silently encounter extra lines. A failed DATA transfer remains failed and
retains any consumed prefix. A receipt must never be inserted inside binary IQ.

No extra gain write, PHY call, calibration override or unrelated register dump
is part of this proposal. In particular, it does not read NVS calibration
contents or change RTC, calibration mode, filter tuning or PLL policy. The
pinned [PHY calibration path](https://github.com/espressif/esp-idf/blob/25fe69f946311abdaf9ad56591f25fedbc20ac98/components/esp_phy/src/phy_init.c#L885)
is relevant background, not evidence of a calibration fault in this board.

## Prerequisites and acceptance of the diagnostic receipt

Before implementation or installation, declare the change in OpenSpec and
review a separate diagnostic profile with exact committed source bytes,
instrumentation diff, SDK/config provenance, flash layout, sizes and all part
hashes. Keep the existing receiver allowlist unchanged. Build through the
locked Nix firmware shell and documented Task bindings. Tests must exercise
register transitions and response ordering at the actual acquisition
boundaries, plus malformed stages, timeout prefixes, buffer bounds and cleanup;
parser fixtures alone do not establish correct firmware observation.

The sole hardware operator must confirm the stable ESP identity, exclusive
UART ownership, preserved original image and an independently read current
full-flash baseline before installation. On every attempted install, failure
or cancellation, close all owned UART groups before restoring and verifying
all original flash bytes and the original reset boot. If group closure cannot
be established, report restoration unverified rather than racing another UART
owner. This proves restoration at that boundary, not electrical power removal.

Receipt validation must require exact typed stage names/order and capture
ordinals, bounded field values, nondecreasing firmware times and honest host
full-line brackets. Each of the 20 successful payloads must contain exactly
40,950 bytes and pass its reported sample count, CRC32, saved length and SHA-256
checks. Check both complete-run totals and failed prefixes. Reject missing,
duplicate, reordered or contradictory records. Timestamp brackets remain
nominal observations with uncalibrated register-to-RF and UART latency.

Persist bounded IQ/wire buffers only after UART closure, with verified saved
lengths/hashes and explicit persistence failures. Use fresh ignored private
directories with mode 0700 and files mode 0600. Publish only allowlisted numeric
register fields, stage/timing/integrity metadata and artifact provenance.
Keep raw UART, IQ, boot bytes and identifiers private; publish no unrelated
register or calibration contents. Installation/restore receipts and independent
offline replay are required before recording a completed hardware diagnostic.

## How to interpret either result

If bit23 remains one and the forced-selector field remains 48 at every sampled
stage, report that readback consistency. It narrows a persistent selector-field
mismatch explanation for this new run; it does not prove continuity between
reads, effective analog gain, correct tuning, sensitivity or reception.

If a field changes or differs from the requested selector, retain its exact
stage and integrity context as a new configuration-readback observation.
Do not attribute the fresh SDR nulls to it, infer past state or automatically
rewrite the setting. Any controlled reapplication or source-response comparison
requires a separate prospective protocol.

Neither outcome accepts an SDR packet or supplies transmitted-event counts.
The complete-window, protected CRC24, exact owned AD, deduplication and source
qualification requirements in [the BLE plan](ble-next-trial.md) remain intact.
This planning document records no physical result and leaves those gates open.
