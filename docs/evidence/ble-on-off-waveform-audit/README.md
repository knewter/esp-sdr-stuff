# Source brackets do not establish an owned RF response

Offline at root `566fb8b`: all 1,251 A / 997 C payloads passed SHA/CRC/count
checks. Independent command-to-payload brackets reproduce every 1-second-guarded
phase, retaining 39/33 transitions. No decoding or hardware.

[Results](results.json): C nominal +1.5..+2.5 MHz median power is 2.00–2.16
code² across ON/OFF. Its enable-edge ratios are 0.957/1.030/0.993;
A's are 0.682/0.894/1.009. There is no repeated increase. C AC drops across
both enable and disable edges. These are descriptive 10-second medians, not
significance tests. C ON0/OFF1 AC q90 is 127,821/129,531 code²; rail q90
4.35%/4.37%. Low pooled medians conceal large OFF excursions.

[Source](analyse.py): centered AC, Hann band power normalized by N×window
energy, rail fraction and block32 q90/median. Synthetic amplitude-two in-band
power reproduces 4 code²; out-of-band leakage <1e−9; signed packing edges pass.
Band choice comes from [historical positives](../ble-waveform-comparison/README.md).

Repeat with private inputs/fresh output:
`nix develop .#ci --command task -t docs/evidence/ble-on-off-waveform-audit/Taskfile.yml audit -- --root "$PWD" --output "$PWD/.scratch/on-off-next.json"`

Sparse snapshots do not calibrate gain/SNR or count emissions. Unknown
interference/state remain competing causes. Later [stable register fields](../receiver-register-observation-002/README.md)
do not retrospectively prove analog gain. Five historical positives / 2,248
fresh nulls remain unchanged; no acceptance gate closes.
