# Prospective same-waveform precision diagnostic

Declared October 4, 2026, before implementation or outcome replay. This is an
offline diagnostic of deterministic upper-bit reduction, separate from actual
8-bit acquisition, radio reception qualification and the counted-source trials.
No device is opened and no existing physical gate or accepted requirement changes.

Freeze all246 historical `rf-controls-trial` rows and all1010 fresh
`ble-matched-gain-001` manual-gain rows. The latter is the complete matched
manual dataset, not the later also1010-row RF004 ladder null. Preserve every
row, source-phase label, null, foreign-redacted packet and transport outcome.
Each original raw file stays read-only. Private input receipt SHA-256 is
`9166c1775adf8d1d96e52288ef98a1915789b9b4e2969465ba91c6d3eb98184b`; it binds every original path, byte count and hash, exact CSVs,
receiver manifests, reference phase/report files and runtime source files.
Public CSV hashes are `aa86c97b5ba4a1bfe1d9a093436883ba07317e82b7b10a3bff245253663c9739`
and `23a622b9739d4e2225de0d3558b74acc1eebc7d0ba1fd8a218e23eb328c16344`.
Receiver manifest hashes are `81c02de86936ac80fc903115b811502276d86fbe4fa3c2c7f24b0130ed69b981`
and `47f6a62a52b28671ad81af8f3351c3bad877f134cfc51717096c2e51d6f32119`.
Recheck exact returned sample count16380, bytes40950, SHA and expected/actual
CRC32 before decoding. Any failed row remains explicit and supplies no success;
missing/mutated source artifacts stop the run rather than silently omit rows.

Convert each signed10-bit component with arithmetic `value >> 2`, then encode
signed8-bit bytes. Independently extract bits2..9 from every unsigned10-bit
field in each little-endian40-bit/two-IQ group; require byte equality. Exhaustively
check all1024 input values, signed edges and independent packing, without using
the production unpacker as the reference. No centering, scaling, saturation,
resampling, noise or low-bit rounding occurs before this conversion. Save all
derived raw bytes privately (0700 directories,0600 files), with original/derived
hashes, sizes and CRC32 lineage. Derived bits are not measured new RF data.

Use unchanged decoder SHA-256
`834fdd78e3221d0625eaa7cf1059b9bd59d3b8b9fa929578f2555bff64130128`,
nominal16MS/s,16380 pairs,channel37, exact known manufacturer AD and refinement.
Original10 and derived8 receive identical blind bounds. Historical rows explicitly
use their frozen requested LO:2401MHz translates by−1MHz;2402MHz translates by0.
Matched manual rows all use−1MHz. No frequency choice depends on packet outcomes.
Search public AA only: coarse four samples/symbol; correlation>.78; AA errors≤2;
refinement13 periods3.97..4.03,17 offsets±2 samples at.25 spacing,37 threshold
biases−.45..+.45 at.025 spacing, at most32 candidate clusters per capture. No
payload-assisted tuning/repair, expanded search or decoder edits after labels.
Keep every candidate status, including failures and truncations; foreign payload
and address remain redacted. Count physical full-packet clusters rather than
receiver-hypothesis duplicates. Exact whole owned AD, protected CRC24, bounded
packet fields and complete preamble-through-CRC nominal sample window are
required for a complete-owned claim. Ambiguous clusters remain unresolved.

The paired report records complete-owned/other/failed/null outcomes per row and
original/derived packet hashes. A changed known-owned result receives independent
slicing, register whitening and reflected CRC24 proof from measured samples and
frozen AA-selected hypothesis fields, including window bounds. Keep failed or
null reproductions visible. Final replay verifies every derived byte and frozen
input again; retained run logs record runtime versions and committed script hashes.

Results bound this deterministic transformation and this decoder on these saved
waveforms only. They do not measure actual8-bit mode, analog gain/filter/LO state,
calibrated sensitivity, source emissions, miss rate or repeated spectral response.
Original TrialB prerequisite, >=100 counted emissions and three-response gates
stay open. Earlier failed/null physical trials remain unchanged.

Grounding: [historical ten-bit controls](../evidence/rf-controls-trial/README.md),
[fresh matched manual proof](../evidence/ble-matched-gain-001/README.md), and
[pinned primary firmware packing](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c#L129).
The firmware selects bits2..9 of I and Q and packs ten-bit pairs little-endian.
The [official Bluetooth sample vector](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core_v6.3/out/en/low-energy-controller/sample-data.html)
grounds independent whitening/CRC checks already verified by the decoder tests.
