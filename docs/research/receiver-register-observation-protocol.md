# Bounded receiver-register observation protocol

**UNVERIFIED hardware: declared protocol for the offline implementation.** This makes the
[register-observation design](receiver-register-observation.md) concrete for
OpenSpec and source review. It records no hardware result. Existing SDR artifact
approval, packet acceptance and transmitted-count gates remain unchanged.

## Separate artifact and fixed profile

Proposed artifact profile: `esp32-register-observation-v1`. Proposed INFO
identity: `ESP32REGOBS1`, with an explicit diagnostic revision. The source base
is receiver `550fadea4d00a9e26ce921c5832167becb3dc20c`; the SDK remains
`25fe69f946311abdaf9ad56591f25fedbc20ac98`. The diagnostic diff is separately
committed, reviewed and hashed. UART is 921600 baud; target is the original
ESP32, with the existing reviewed flash layout and security-disabled policy.

The host applies `FREQ 2401`, `BANDWIDTH 20` and `GAIN MANUAL 48` exactly once,
in that order, requiring their successful replies. The fixed acquisition is
20 `CAP20 16380 6` snapshots: ten-bit components, nominal 16 MS/s and 40,950
payload bytes each. Placement remains as found. There is no Bluetooth source
control, decoding, gain reapplication, retune, retry or resynchronization in
the acquisition loop.

`filter_code=64` is the original-ESP32 helper's mapping of requested 20 MHz:
the pinned [ESP32 curve contains `{64,20}`](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/common/rx_bandwidth.h#L53-L57).
The [integer interpolation](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/common/rx_bandwidth.h#L92-L98)
returns `48 + (16*5 + 5/2)/5 = 64` at 20 MHz. The receiver's
[BANDWIDTH handler](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L198-L200)
uses that helper. This establishes the requested capacitor code, not calibrated
filter bandwidth or continuous verification of the temporary analog setting.

The new measured variable is the forced-selector field readback
`(RX_GAIN >> 24) & 127`, alongside `(RX_GAIN >> 23) & 1`. A successful
[MANUAL command assigns gain_code directly](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L216-L217).
[apply_gain](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L158-L162)
writes `(old & 0x007fffff) | (gain_code << 24) | BIT(23)`. Thus selector 48
intends bits24–30=48 and bit23=1; the full word is not constant. This is a
firmware write/readback interpretation, not live AGC-index semantics or
calibrated analog gain.

## Command and receipt contract

The absolute host deadline starts immediately after exclusive UART ownership,
before synchronization, INFO/LIMITS/BAUD checks or the first setting command.
It includes startup queries, setting replies, diagnostic initialization, all
payloads, stage receipts and terminal receipt. Completion must occur within
30 seconds; startup settling or synchronization does not extend that budget.
Every read/write timeout is capped to the remaining budget; no late success
is accepted.

After successful settings, issue `REGOBS1 BEGIN <nonce>`. Nonce is a fresh
128-bit value encoded as exactly 32 lowercase ASCII hexadecimal characters.
BEGIN is permitted once after boot and only for the exact cached fixed profile;
it performs no setting writes. It samples `post_settings` once and replies
with configuration plus that initial record. Changed selector readback is an
observation, not a reason to repair settings or reject BEGIN as malformed.

While armed, permit only exactly 20 `CAP20 16380 6` requests followed by
`REGOBS1 END <nonce>`. Ordinals are assigned consecutively by firmware, 0–19.
Wrong nonce, argument, command, count or state fails the session without a
restart. A second BEGIN cannot restart it. The proposed diagnostic profile
keeps ordinary, unarmed CAP20 responses unchanged. INFO remains `ESP32REGOBS1`
even when unarmed: the new host refuses the old SDR artifact, and default
capture tools cannot mistake this artifact for their existing SDR INFO/profile.

Each successful capture sends its unchanged DATA header and **all 40,950 binary
payload bytes first**. It then sends one diagnostic line carrying the four
stage records and capture completion/count/elapsed metadata. Initial and
terminal receipts use the same framing:

```text
REGOBS1 <eight-lowercase-hex CRC32> <compact JSON object>\n
```

CRC32 covers exactly the JSON bytes between the separating space and newline,
using the same CRC convention as the existing DATA payload. Define it with an
independent known vector and verify both firmware and host implementations.
The entire diagnostic line has a hard 2,048-byte bound. Serialization uses a
fixed buffer and checked lengths, after acquisition cleanup. No receipt is
inserted inside binary IQ. No generic SDK log or command echo is public data.

JSON is ASCII, without floating-point fields. Every object has common keys
`schema` (integer1), `kind`, `nonce` and `revision` (exact diagnostic revision).
Kinds are exactly `config`,
`capture`, `failed` and `end`. Exact field/type allowlists
reject unknown, duplicate or missing keys and booleans used as integers.
Configuration states the fixed profile, requested settings, rate, bits, sample
count, capture count, record limit and host-independent firmware start time.
Stage records have exactly `sequence`, `capture_ordinal` (null only for the
initial record), `stage`, nonnegative firmware `read_begin_us`
and `read_end_us`, `selector` integer 0–127, `bit23` integer 0–1 and
`hook_cycles` integer 0–4294967295. Require
`read_begin_us <= read_end_us` and each record's end no later than the next
record's beginning. Capture metadata carries actual completion flag, actual
count, existing capture elapsed time, payload bytes and payload CRC.
Firmware names and emits only these allowlisted fields, not a full PHY word.

| Kind | Required additional fields and cardinality |
| --- | --- |
| `config` | `profile` = `esp32-register-observation-v1`; `settings` exactly `{frequency_mhz:2401, bandwidth_mhz:20, filter_code:64, gain_mode:"MANUAL", gain_selector:48}`; `rate_hz` = 16000000, `bits` = 10, `samples` = 16380, `captures` = 20, `record_limit` = 81, nonnegative `start_us`, and `records` containing only sequence 0 / post_settings. |
| `capture` | `capture_ordinal` 0–19, `completion` boolean true, `returned_samples` = 16380, `payload_bytes` = 40950, eight-hex `payload_crc32`, nonnegative `capture_elapsed_us`, and `records` containing exactly four stages in order. |
| `failed` | Exact `failure_kind`, actual attempted `capture_ordinal` (0–19 only during an acquisition attempt; null when no acquisition was attempted), `completion`, `returned_samples` and `capture_elapsed_us` holding actual values or null if unobserved, and `records` holding only that attempt's actual available stage prefix. Between captures, before BEGIN, at invalid END or after 20 captures, ordinal/completion/count/elapsed are null and the new prefix is empty; earlier receipts remain retained separately. |
| `end` | `status` = `completed`, `captures` = 20, `pairs` = 327600, `payload_bytes` = 819000, `record_count` = 81, nonnegative `start_us` and `end_us`. No stage records are repeated. |

The implementation review must enforce those exact keys and reject every
extra key. The host stores each complete line's receive-start
and receive-end monotonic/UTC brackets separately from firmware fields.

END succeeds only after all 20 capture transfers and their receipts succeed.
Its totals must be exactly 20 captures, 327,600 pairs, 819,000 payload bytes and
81 stage records; first/last firmware times and local elapsed are explicit.
The host independently verifies payloads, records, totals and its own deadline.
Firmware time and host full-line brackets are nominal clocks with uncalibrated
register-to-RF and UART latency; neither is an exact RF event timestamp.

## Stage placement and bounded RAM

Use a static array of exactly 81 records, each exactly 32 bytes: exactly 2,592
bytes, excluding fixed serialization scratch. Check capacity before every
append. No heap allocation, UART output, hashing or persistence occurs in the
active acquisition interval.

| Stage | Exact proposed boundary in the pinned acquisition path |
| --- | --- |
| `post_settings` | BEGIN, after confirming cached profile, before any capture. |
| `before_acquire` | Validated capture entry, before the first DUMP_CTRL clear, sentinel fill or filter application. |
| `armed_before_trigger` | After filter and dump configuration, before the existing start timestamp and trigger pulse. |
| `dump_complete` | After reading dump result/status and calculating existing elapsed, before clearing dump controls. This records timeout state too. |
| `restored_after_dump` | After SRAM owner, byte selection and filter restoration, before sentinel validation, packing, CRC or UART transmission. |

The four acquisition records come from the
[actual acquire_iq boundaries](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L82-L119).
Read RX_GAIN once per stage, extracting both fields from that same word; do
not read each field at a different instant. Bracket that read with the two
nominal firmware times. Do not add any RX_GAIN or other RF write.
Timestamp/read overhead must be measured and reported, not assumed
zero. The existing capture elapsed field retains its original placement.
The prospective implementation brackets the complete non-inlined observation
body with read-only CCOUNT reads: eligibility/capacity checks, pointer lookup,
both firmware timers, MMIO, original field stores and body entry/return.
`hook_cycles` is their unsigned 32-bit modular difference. Guard the fixed
240 MHz, single-core, disabled power-management configuration. Actual target
disassembly must confirm the bracket before installation.

Report raw hook-body elapsed cycles separately from the shorter read-time
bracket. They include intervening interrupts/preemption and are not deterministic
execution cost. A full counter period (about 17.9 seconds at nominal 240 MHz)
is ambiguous; raw cycles do not prove the absence of a long stall. The two cycle
boundaries, subtraction/final delta store and wrapper/callsite instructions
remain residual measurement overhead. Enumerate those from target disassembly
and state their uncalibrated cost; do not claim zero total instrumentation cost
or calibrated RF perturbation. No benchmark loop is added to acquisition.

The record array and serialization buffer must not overlap the entire reserved
MAC sample slab `[0x3ffe8000, 0x3fff8000)`, including sentinel space. Verify
actual linked addresses and sizes, not only a C section attribute. Generated
linker-map and configuration checks are installation prerequisites. The records
are not sample storage and must survive in-place ten-bit packing.

## Failure and cleanup semantics

Firmware has a local session deadline no later than BEGIN plus 30 seconds and
never starts another capture after expiry. The host's earlier deadline remains
authoritative. Preserve the existing bounded dump wait and unconditional dump,
SRAM/byte-selection/filter cleanup. A timeout is a failed capture, even if
register-stage records exist. Do not invent a successful payload or terminal.

Before DATA begins, a dump timeout or memory-validation failure, after verified
acquisition cleanup, sends exactly one fixed `ERR REGOBS1 <failure_kind>` line
followed by a checksummed typed failed-prefix receipt. Allowlisted failure kinds
are `capture_timeout`, `capture_count`, `capture_memory`, `record_capacity`,
`session_deadline` and `session_state`. Include only the actual stage prefix and
actual completion/count values, with unavailable values null. The host accepts
that framing only as failure. Stop accepting captures in this session. If
UART fails partway through DATA/payload, do not append text into that incomplete
binary frame; the host closes on failure/deadline and retains consumed bytes.
Terminal success must never follow an earlier failure.

Source-review clarification before any build: if the entire DATA header and
binary payload finished before a post-transfer deadline/error is detected,
firmware may emit the fixed ERR line and typed failed receipt after those
complete bytes. The host independently verifies and retains that binary frame
as a failed observation; it does not count a successful diagnostic capture or
terminal. This permission never applies to partial DATA/header/payload, where
text remains prohibited. Failure ordinals describe an actual acquisition
attempt, never an invented ordinal 20 or a previous completed attempt.

The host maintains bounded RAM buffers for consumed UART and payload bytes,
closes its UART before persistence, and distinguishes bytes consumed from
verified saved bytes/hash. Use fresh ignored private directories mode 0700 and
files mode 0600. A short write, OSError, reread mismatch or hash failure remains
failed with explicit persistence uncertainty and preserved accessible prefix.
Public receipts expose only allowlisted numeric fields, bracket/integrity
metadata and artifact hashes. Raw IQ/UART/boot, USB identity and personal paths
remain private. No calibration/NVS/RTC dump is collected.

The exclusive operator confirms stable identity, ownership and preserved
original flash; independently read all current 4 MiB and require a baseline
match before installing. The separate installer validates exact diagnostic
profile/version, committed source and diff hashes, source-base/SDK pins,
generated configuration, security policy, target, offsets, lengths and every
part hash. It must reject the diagnostic through the unchanged SDR allowlist,
then explicitly accept it through its own narrowly reviewed guard.

Every attempted install requires complete owned UART-group closure before full
original-flash restoration, independent full readback and matching reset boot.
Failure/cancellation takes the same restoration path. Unknown group closure
blocks competing restoration and records recovery unverified. No electrical
power-removal claim follows from reset restoration.

## Offline tests required before hardware

| Test boundary | Required concrete checks |
| --- | --- |
| Actual C MMIO path | Compile the instrumented acquisition functions with controlled REG_READ/REG_WRITE, DPORT, ROM/filter, timer and UART shims. Verify real function read/write order, same-word field extraction, all four stages and no added gain write. Do not replace acquire_iq with a test stub. |
| Selector transitions | Supply independent register words for each stage, including 48/bit1, changed selector and bit0. Verify exact observations, no repair and preserved lower bits in the original manual application. |
| Timeout and memory errors | Exercise completion timeout, wrong hardware count and inside/outside-slab sentinel failures. Verify restoration, actual prefix, no payload success and no later captures/terminal success. |
| RAM and timing | Reject the 82nd append; verify map ranges and packing cannot modify stored records; exercise deadline before capture and during response. Report added reads/timing separately from RF claims. |
| Real response ordering | UART shim sees complete DATA header/payload before any stage line. Failed/partial binary send produces no interleaved text. Check maximum line length and an independent metadata CRC vector. |
| Host parser | Mutate an independently generated C transcript: wrong nonce/version, duplicate JSON keys, booleans, wrong count/CRC/length, missing/duplicate/reordered stage, timestamp regression, late END and early terminal. Each stays failed. |
| Persistence and lifecycle | Inject storage errors and cancellation before/during capture. UART closes before saved-byte verification; unknown process-group closure blocks restoration; verified closure permits exactly one complete restoration attempt. |
| Artifact isolation | Alter source/config/part hashes, SDK/target/layout/security, profile or map ranges. Refuse installation before opening hardware; unchanged SDR guard rejects the new INFO/profile. |

After source review, commit the scoped implementation before a fresh Nix-only,
bounded build. Independently review the actual artifact, generated config/map,
host tests and frozen caller before the sole operator runs one declared trial.
No build or physical trial is performed by this planning step.

## Host lifecycle and repeatable commands

The separate supervisor checks committed caller bytes and the narrow artifact
guard before hardware access. Its run action independently reads the current
4 MiB and requires the preserved baseline, then validates the artifact again
before writing its canonical three parts. Diagnostic image headers are 2 MiB;
the physical preservation/restoration remains the entire 4 MiB. The original
SDR installer/allowlist is unchanged.

The acquisition worker starts its absolute 30-second deadline immediately after
exclusive UART ownership. The supervisor drains stdout/stderr into separately
bounded 512 KiB RAM buffers and imposes a 60-second process deadline including
startup and post-close persistence. That outer deadline never extends the
acquisition budget. Parent logs are saved only after complete worker-group
closure. Unknown closure blocks restoration. Cancellation/failure after an
installation attempt takes the same full-flash/readback/reset-boot path.

Before a successful public result, independently parse saved original UART
framing, metadata CRCs, exact DATA binary boundaries and typed receipt order;
bind those bytes to worker metadata and independently reread/hash all saved IQ.
A hash of the whole wire or regenerated metadata CRC alone is insufficient.
Failed/truncated bytes remain private and are never converted into completion.
Before the first diagnostic line, retained startup noise may span more than
2,048 bytes without a newline. Bound that uninterpreted private prelude by the
whole-worker wire budget; the first diagnostic candidate and all subsequent
protocol lines retain the strict 2,048-byte limit. Do not resynchronize after
a malformed diagnostic candidate or skip it to find a later valid receipt.

```sh
nix develop .#ci --command task register:check
nix develop .#ci --command task register:artifact:check -- --artifact .scratch/REGISTER_ARTIFACT
nix develop .#firmware --command task register:observe -- --artifact .scratch/REGISTER_ARTIFACT --manifest .scratch/REGISTER_ARTIFACT/manifest.json --private .scratch/FRESH_REGISTER_RUN --output docs/evidence/FRESH_REGISTER_RUN
nix develop .#firmware --command task register:restore -- --private .scratch/FRESH_REGISTER_RESTORE --output docs/evidence/FRESH_REGISTER_RESTORE
```

These are prospective physical bindings, not installation approval. A fresh
corrected build, actual linked allocations/disassembly, frozen supervisor and
independent review remain prerequisites for the first run.

## Decision and limits

A complete diagnostic can report field retention or sampled discrepancies with
their exact stage context. A discrepancy does not invalidate an otherwise
integrity-valid observation, imply analog gain or explain past captures. It
never triggers automatic repair. Consistent selector 48/bit23=1 does not prove continuity,
tuning, sensitivity or SDR reception. Failed acquisition/transport/persistence
or restoration remains failed and retains its prefix.

The [existing BLE protocol](ble-next-trial.md) still requires its original
complete nominal packet window, protected CRC24, exact owned AD, deduplication
and separately qualified source denominator. No detection rate, SDR-positive
prerequisite or emitted-event count is supplied by this register diagnostic.
