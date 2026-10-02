# Independent paired replay confirms nulls and a historical regression

The [DC-first comparison](../ble-dc-first-replay-001/README.md) passes
independent saved-data integrity review. The processing variant **does not
recover a fresh packet and is not adopted as the default**. This is an offline
software result; it creates no live reception evidence or RF/count acceptance.

[Checks and exact hashes](checks.json) identify predeclared protocol `abe858e`,
processing commit `3a0b6dc`, public evidence `05cbcef`, four private full-result
hashes and the independent replay. Both public files equal their committed
bytes, and every compact summary count, input hash and historical regression
case matches independently reproduced data.

| Dataset | Captures checked | Original owned results | DC-first owned results |
| --- | ---: | ---: | ---: |
| Fresh A, 8-bit | 1,251 | 0 | 0 |
| Fresh C, 10-bit | 997 | 0 | 0 |
| All historical 8-bit | 549 | 4 | 1 |
| All historical mixed 10-bit | 246 | 1 | 1 |

The reviewer verified every original payload's SHA256, CRC32, count and length,
used an independent five-byte signed 10-bit reader, and manually subtracted
`sum(I)/N + j·sum(Q)/N` from the entire capture. Both methods then called the
unchanged core directly; the new wrapper was **not imported as the replay
oracle**. Rate, channel, bounded refinement and all packet policies remain
unchanged. The full paired replay took 38.10 seconds under locked Nix and an
ignored Task recipe. All 3,043 original and centered frame-record collections
agree with the operator's results. Numerical metadata uses the recorded tight
floating tolerance after normalizing NumPy scalars to JSON types; CRC/AD flags,
integer fields, statuses and protected-PDU hashes match exactly.

Historical mixed controls retain each row's declared LO: **222** use −1 MHz
translation and **24** use zero. Historical 8-bit captures **435, 464 and 499**
lose their verified result under DC-first processing. Capture **511** remains,
as does 10-bit capture **103**. Both retained results have the original protected
PDU hash `177ba70a…`, CRC24, whole exact owned AD, type/length, one owned solution
per snapshot and complete nominal preamble-through-CRC windows inside 16,380
samples. The review checks these bounds independently; no incomplete prefix or
access-address-only candidate is counted. All five original accepted receipts
remain unchanged.

The five wrapper vector tests independently pass. An additional synthetic check
modulates the independently published SIG vector with DC `32−16j`, +1 MHz
carrier and deterministic noise, then uses manual centering and the unchanged
core. The valid vector yields one redacted verified result; flipping protected
bit 40 without updating its CRC yields `crc_failed` and no verified result.
These checks verify software behavior, not RF reception, and use no payload
repair or waveform selection.

Detailed result files remain ignored, now verified at mode 0600 under a 0700
folder; permission hardening changed no recorded content hashes. Raw complex
IQ, foreign payloads, addresses and raw bit streams are not published. No new
images are needed for this null/regression result.

This rejects a claimed DC-first improvement on the preserved fresh data and
records loss of three historical successes. It does not establish why either
physical session was null, prove a source or gain fault, compare emitted rates,
calibrate sensitivity, release conditional Trial B, or close RF/count gates.
The [original waveform audit](../ble-waveform-comparison/README.md) remains a
separate measurement of ADC distributions and existing preprocessing.
