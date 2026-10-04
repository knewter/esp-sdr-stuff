# Same-waveform precision diagnostic: offline preparation

The [prospective protocol](../../research/ble-same-waveform-precision-protocol.md)
was committed before code or replay. This experiment compares the same measured
ten-bit waveforms with deterministic upper-eight-bit conversions. It measures
no new RF reception, source emissions or actual eight-bit hardware behavior.
All existing physical gates and original Trial B remain unchanged.

Seven focused diagnostic groups and sixteen original decoder/independent-review
groups pass with locked Nix/Task. They verify all1024 signed input values,
independent little-endian40-bit packing, signed edges, no preprocessing or
rounding, complete-window/cluster policy, transport hash/CRC/count refusal, and
independent SIG-vector waveform slicing/whitening/reflectedCRC24 at both formats.
Initial mistakes in two expected literal test values are retained privately;
corrected independently calculated constants pass. Decoder bytes remain frozen.

The private input receipt binds all246 historical control-sweep captures and
all1010 fresh matched-manual captures. Input CSVs, receiver manifests, original
SHA/size/count/CRC and source labels are rechecked; no row is selected by its
packet outcome. All derived bytes and per-row receipts remain private. The
script saves each completed row before continuing, and only a complete final
report with post-run input/artifact verification can represent a finished replay.
Missing/mutated inputs abort, leaving previous row receipts for diagnosis.

Preparation supplies no paired reception result yet. Independent full replay
and publication of the bounded deterministic result are still pending.
The private repeated commands are:

```text
nix develop .#ci --command task --taskfile .scratch/precision-001/task.yml test
nix develop .#ci --command task --taskfile .scratch/precision-001/task.yml replay
```

No hardware port, Bluetooth controller, FPGA, vendor tool or container is used.
