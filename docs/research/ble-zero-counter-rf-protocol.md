# RF discriminator for a zero controller counter

This prospective protocol is committed before receiver acquisition. Source-only
diagnostics on handles `0xEF` and `1` returned a matching duration-expiry event
(`0x3C`) with completed-event count **0**, independently visible in sanitized
source and monitor records. No receiver waveform accompanied those diagnostics.
The zero controller field does not establish zero RF emissions. This experiment
distinguishes that interpretation from a controller-counting limitation.

## Fixed acquisition

The root operator exclusively owns the ESP32 port and Bluetooth controller.
Use preserved, verified experimental firmware with the 921600-baud transport;
restore and verify the original image afterward. This protocol authorizes no
additional operator or source-side fallback.

Record an approximately **80-second** receiver dataset at LO **2401 MHz**,
filter **20 MHz**, manual gain **48**, nominal **16 MS/s**, **8 bits per
component**, and **16,380 complex samples** per snapshot. Preserve every
snapshot, its transport CRC/count result and monotonic acquisition brackets.
Keep full raw IQ in ignored private storage, outside Git and the site.

Begin receiver acquisition at least **five seconds before** the first source
enable. Predeclare ten episodes, `zero-counter-01` through `zero-counter-10`,
all on advertising **handle 1**. Each episode configures legacy nonconnectable
properties `0x10`, LE1M, primary channel 37 only (2402 MHz), **20 ms** interval,
**5-second duration** (500 units of 10 ms), and **MaxEvents 255**, nonzero.
Use the exact manufacturer AD structure
`0fffffff4553502d5344522d4556414c` (`ESP-SDR-EVAL`). Disable/remove that handle
and record successful cleanup after each episode. Wait **one second OFF**
between successive episodes. Continue receiver acquisition for **more than ten
seconds after** the final source socket closure/cleanup; extend the run if
command overhead would otherwise shorten that tail. Preserve all ten episodes,
including failures, missing events and zero-counter records. Do not restart a
failed episode silently or replace it with a successful one.

A separate read-only monitor records sanitized accepted parameters, exact-data
match, enables, observed terminations and cleanup. Store the source script hash
and each actual observed status/count. Requested MaxEvents is not an emitted
count. A nonzero counter, if unexpectedly observed, remains its original field
and requires separate review; it does not silently change this protocol.

## Blind offline replay

Replay **every** waveform with `tools/ble_decode_iq.py`, channel 37, nominal
16 MS/s, 8-bit components, 16,380 samples, digital translation **−1 MHz**, and
the committed blind bounded AA-trained refinement (`--refine`). Its search uses
the public advertising access address; known-marker bits must not train,
repair or select a receiver hypothesis. Check the waveform SHA-256, byte length
and transport CRC against every physical capture row before analysis. Preserve
all captures and decoder failures, rather than selecting only promising dumps.

Example replay, with private input and a fresh redacted output:

```sh
python3 tools/ble_decode_iq.py --input PRIVATE-IQ-DIRECTORY \
  --output FRESH-DECODER-MANIFEST.json --rate 16000000 --bits 8 \
  --samples 16380 --channel 37 --frequency-translation-hz -1000000 --refine
```

Join same-machine monotonic source and receiver records for every episode and
all OFF intervals. A packet is unambiguously inside an episode only when its
entire host acquisition bracket, from command send through header receipt,
lies after that episode's enable send and before its observed termination.
Report boundary captures separately. Host brackets are control-plane timing,
not hardware RF timestamps.

## Decision and publication

A positive discriminator requires a complete, strict CRC24-valid
ADV_NONCONN_IND packet (type 2, PDU length 22) containing the exact whole owned
AD structure, with its full nominal preamble-through-CRC window inside one
snapshot, wholly associated with a zero-counter episode. Retain waveform/PDU
hashes, packet bounds, AA/preamble errors and independent reproduction. Collapse
timing/slicer hypotheses within each four-microsecond access-start cluster.
Two distinct exact-marker clusters inside one 1.024 ms snapshot are incompatible
with this source's minimum 20 ms interval and require unresolved-provenance
review; never count both as source events.

Such a positive packet demonstrates actual owned reception associated with an
episode despite its controller field being zero, falsifying the interpretation
that this zero counter proves no emission. Failure to find a verified packet
is **inconclusive**: sparse snapshots, acquisition settings and bounded decoder
sensitivity can all hide a transmitted packet. A failed or truncated AA-only
candidate cannot establish owned reception.

Report per-episode and OFF capture counts, distinct verified receptions,
excluded boundary candidates and source statuses honestly. **Actual RF event
count remains unknown**; publish no hit rate using zero or requested 255 as
the denominator, and do not accept the proposal's ≥100 counted-event gate.
The original count-limited and prospective timer-count criteria remain
unchanged. This diagnostic is not a completed counted trial.

Publish redacted manifests and, if a verified positive makes it useful, one
amplitude-only packet-envelope plot labelled as actual reception. Smooth and
discard waveform phase; publish neither raw IQ, addresses nor foreign payloads.
Site screenshots prove presentation only. Independent replay and committed
physical evidence precede any hardware-task acceptance.
