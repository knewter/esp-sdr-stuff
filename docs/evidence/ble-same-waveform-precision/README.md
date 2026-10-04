# Two saved owned packets survive upper-eight-bit conversion

Recorded October 4, 2026. All **1,256 saved ten-bit waveforms** were paired with
exact upper-eight-bit conversions and decoded using unchanged blind bounds.
Both previously verified owned packets remain complete and CRC-valid in the
derived format, with the same protected PDU hash. The other1,254 pairs contain
no complete owned packet in either format; neither set produces foreign
CRC-valid packets. This tests deterministic digital precision on the same saved
samples. It measures no new RF capture or actual eight-bit receiver behavior.
Independent whole replay and lineage/packet review pass.

| Saved dataset | Waveform pairs | Complete owned original / derived | Remaining pairs without complete owned packet |
| --- | ---: | ---: | ---: |
| Historical gain/filter controls | 246 | 1 / 1 | 245 |
| Fresh matched manual48 control | 1,010 | 1 / 1 | 1,009 |

The packets are historical capture103 and matched-manual capture48. All four
format/packet instances pass separate AA-selected waveform slicing, register
whitening, reflected CRC24, exact whole owned AD and nominal complete-window
checks. They share protected PDU SHA-256
`177ba70ae0be7ffff890d04b3214f18a46cfe85e47b485bf82dd5c534c53aa45`.
No known payload trains or repairs a receiver hypothesis. The full waveform
hashes remain distinct; this is two original waveforms and their digital copies.

[Every paired row](paired-captures.csv) retains original source-phase labels,
waveform hashes, original/derived sizes and CRC32, per-format candidate-status
counts, redacted foreign counts, complete packet proofs and cluster ambiguity.
[Checks and exact inputs](checks.json) bind the completed private report, all
original files, receiver manifests and script/decoder revisions. Raw ten-bit
waveforms and every derived eight-bit file stay private. Zero null/foreign rows
are selected away; unknown source emissions supply no rate denominator.

The [prospective protocol](../../research/ble-same-waveform-precision-protocol.md)
was committed at `fbc9d61` before implementation or outcome replay. It fixes
all246 [historical controls](../rf-controls-trial/README.md) and all1010
[fresh matched-manual captures](../ble-matched-gain-001/README.md). The second
set is distinct from the later RF0041010-row ladder null. Historical requested
LO2401/2402 determines translation−1MHz/0; all matched rows use−1MHz. Both
formats use nominal16MS/s,16380 pairs,channel37 and the same frozen AA-only
coarse/refinement search. No decoder or frequency setting changed after labels.

Every source component is reduced with signed arithmetic shift by2. Independent
LE40 extraction verifies byte equality before replay; an additive third literal
byte-mask formulation independently reproduces **every derived byte** afterward.
There is no centering, scaling, rounding, saturation or resampling before the
conversion. All51,433,200 original bytes and41,146,560 derived bytes pass count,
SHA/CRC and post-run artifact checks. All1,256 durable per-row receipts match
the final report. Output directories/files have0700/0600 permissions.

Seven focused diagnostic groups and sixteen unchanged decoder/review groups
pass with locked Nix/Task. They verify all1024 signed input values, independent
packing, signed edges, conversion policy, window/cluster refusal, transport
hash/CRC/count checks and independent SIG-vector waveform CRC/whitening at both
formats. Two initially incorrect expected literal test constants are retained
privately and corrected by independent bit arithmetic. OpenSpec validation passes.
The repeated private commands are:

```text
nix develop .#ci --command task --taskfile .scratch/precision-001/task.yml test
nix develop .#ci --command task --taskfile .scratch/precision-001/task.yml replay
```

These two successful waveforms tolerate upper-bit reduction with this frozen
decoder. The result does not establish actual eight-bit capture-mode equivalence,
calibrated sensitivity, analog gain/filter/LO behavior, a three-cycle source
response, independently emitted events, a hit/miss rate or the cause of separate
physical nulls. Original TrialB and all physical RF/count gates remain open.
Earlier failed and null experiments stay unchanged. No device, FPGA, vendor
software or container was used for this offline replay.

An isolated peer replay of all1,256 pairs exactly reproduces every author
report field except elapsed runtime. Independent literal LE byte extraction
checks every derived byte and all1,024 signed values; exact CSV membership,
source phases, per-row receipts, sample counts, SHA/CRC and private modes pass.
The peer separately re-slices all four owned packet instances and verifies
register whitening, reflected CRC24, whole owned AD, protected PDU hashes and
nominal complete windows. Each selected preamble retains one hard-decision
error; complete-window claims do not assert a perfect preamble.

Seven diagnostic and sixteen unchanged decoder groups pass again. Nine peer
corruption/refusal probes cover altered raw bytes, CSV digest, CRC/count,
production unpacking, runtime freeze, row order, original digest and a corrupted
newly written derived file. Earlier audit attempts remain private: repeated
negative-probe output paths were corrected to fresh paths so refusal proves
the intended corruption, rather than a reused-directory check. No product
failure was found in this review. The [checks](checks.json) bind the peer
receipt, replay and independent audit source. Physical gates remain open.
