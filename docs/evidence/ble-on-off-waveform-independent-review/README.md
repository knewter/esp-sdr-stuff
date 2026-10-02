# Independent guarded waveform review

**PASS**, offline 2026-10-02. A different agent reviewed DSP commit `d3d8efc`
against baseline `566fb8b`, without hardware access, decoder changes or new
acceptance claims. [Checks and exact hashes](checks.json).

The locked Nix/Task audit replayed all 2,248 private payloads and reproduced
[results.json](../ble-on-off-waveform-audit/results.json) byte-for-byte. Every
SHA256, transport CRC, length and sample count passed. Separate calculations
checked contiguous unique indices, private/public source and CSV equality,
signed packing, all phase summaries and all twelve local edge ratios. Independent
interval construction used whole command-start through payload-receipt brackets
with the declared one-second source guards, preserving 39 A / 33 C transitions.

A separate bit-array ten-bit reader and direct Parseval check support the
normalization. The reported band metric is integrated Hann-window power in
code², not density per Hz. An amplitude-two complex in-band tone gives 4 code²;
an out-of-band tone leaks less than 1e−9. Both signed endpoint vectors pass.
The block32 statistic uses 16,352 samples, excluding the final 28; endpoint
fractions use all I/Q components and the exact signed endpoints.

The [audit's interpretation](../ble-on-off-waveform-audit/README.md) is supported:
there is no repeated enable-edge band-power increase; C also has large OFF
excursions. These descriptive ratios establish neither significance nor an RF
cause. ADC-code power/rails do not calibrate analogue gain or SNR. Host/controller
latencies and the nominal frequency/time axes remain uncalibrated. Sparse
captures do not count emissions or prove absence of owned RF. The five historical
positives, 2,248 fresh nulls and original gates remain unchanged.

Only this compact receipt is public. Raw waveforms and supplemental replay
outputs remain ignored and private; no device addresses or payload bytes are
exported. No blocking correction was found.
