# DC-first replay does not recover a fresh packet

The [predeclared paired method](../../research/ble-dc-first-replay.md) completed
saved-data replay of all **3,043** captures on 2026-10-02. Every input passed
saved length, sample count, SHA-256 and CRC32 checks. The core decoder remained
byte-for-byte unchanged; the separately named wrapper subtracts the entire raw
capture mean before its original translation and bounded decoding pipeline.

| Dataset | Captures | Original owned CRC24 matches | DC-first owned CRC24 matches |
| --- | ---: | ---: | ---: |
| Fresh A, 8-bit | 1,251 | 0 | 0 |
| Fresh C, 10-bit | 997 | 0 | 0 |
| All historical 8-bit | 549 | 4 | 1 |
| All historical mixed-settings 10-bit | 246 | 1 | 1 |

This isolated processing variant **is not adopted as the default**. It recovers
no fresh packet and loses historical captures 435, 464 and 499. Captures 511
and 103 retain the same owned protected-PDU hash. Original null receipts and
all five historically accepted packets remain unchanged. The comparison does
not attribute the nulls to DC, low ADC power, gain or a source fault.

The [summary](summary.json) records source/input hashes, all paired totals,
private full-result lengths/hashes, candidate windows and actual runtimes.
The complete per-capture records remain private; no failed outcome is discarded.
Mixed historical controls use each row's declared frequency translation,
including zero for LO 2402 MHz and −1 MHz for LO 2401 MHz.

## Method and verification

[The wrapper](../../../../tools/ble_dc_first_replay.py) calls the unchanged
decoder with its original resampling, access-address search, refinement bounds,
whitening, CRC, whole-AD policy and cluster deduplication. It does not use source
phases, packet positions or known payload bits to choose mean removal.
Five synthetic checks use the independently published Bluetooth SIG vector
with a large DC offset, translated carrier, noise, truncation and offset-only
inputs. Those checks pass and remain software evidence; their success did not
predict a successful physical-data replay.

The owned matches in this table are paired decoder outcomes, not a claim of
new physical reception or a newly accepted complete packet. Independent
whole-waveform review and the original complete-window/protected-PDU gates
remain required for any new packet claim. Neither method produces an emitted
denominator, detection rate, calibrated sensitivity or Trial B admission.
No hardware, source or receiver firmware was changed by this replay.

Each dataset ran through locked Nix and `task decode:ble-dc-first` after the
wrapper was committed at `3a0b6dc`. For example, choose a fresh private output:

```sh
nix develop .#ci --command task decode:ble-dc-first -- --captures docs/evidence/ble-bluez-control-001/captures.csv --private .scratch/ble-bluez-control-001/iq --bits 8 --output .scratch/dc-first-next/a.json
```

The [waveform comparison](../ble-waveform-comparison/README.md) is a separate
audit of original preprocessing and ADC distributions. The
[receiver-register protocol](../../research/receiver-register-observation-protocol.md)
remains a prospectively declared hardware diagnostic, not a result of this replay.
