# Replay saved IQ with DC removed before frequency translation

**Prospective: no corrected decoder result is recorded here.** This is a
software diagnostic for the fresh [8-bit](../evidence/ble-bluez-control-001/README.md)
and [10-bit](../evidence/ble-bluez-control-002/README.md) null controls. Their
original manifests, fixed-decoder nulls and RF/count gates remain unchanged.

## One declared processing change

The current [decoder](../../tools/ble_decode_iq.py) translates raw IQ before
subtracting its mean. A constant raw offset therefore becomes a rotating tone;
subtracting the translated mean does not remove that tone. Whether its
magnitude affects these captures is a measurement question. This code-order
observation alone proves neither missed packets nor their cause.

Introduce a separately named wrapper that subtracts the mean of **the entire
raw capture**, then calls the existing decoder with its original translation,
resampling, access-address search, timing/refinement bounds and packet checks.
Keep the existing decoder and its default behavior unchanged. The additional
mean subtraction uses no packet location, known payload bits, source phase or
marker agreement. It changes no search budget, thresholds, carrier/rate grid,
whitening, CRC, polarity selection or packet deduplication.

Replay every saved waveform in controls A/C: 1,251 eight-bit and 997 ten-bit
captures, nominal 16 MS/s, 16,380 pairs, channel 37, translation −1 MHz and
the original blind refinement. Verify each private byte length, SHA-256 and
CRC32 against its committed capture CSV before decoding. Run the original
method as the paired reference, or use its independently reproduced full
receipt after verifying exact decoder/input hashes. Retain every outcome,
including nulls and failures. Do not select captures by corrected success.

Also replay all 549 historical eight-bit captures and the complete historical
mixed-settings control set using its per-capture declared LO/translation,
rather than only the five known positive windows. Preserve the five historical
protected-PDU hashes as regression evidence; failure to reproduce one is
reported explicitly and does not rewrite its original valid receipt.

## Acceptance and reporting

Run independent Bluetooth SIG vector tests with a deterministic raw DC offset,
carrier translation, noise, corruption and truncation. Label these synthetic
software checks. A correct preprocessing result is not RF evidence.

For a physical owned-packet claim, independently replay the saved original
bytes and require a complete nominal preamble/access-address/PDU/CRC window,
protected CRC24, whole exact owned AD and one solution per access-start cluster.
Raw access-address correlation or an incomplete CRC-valid prefix is insufficient.
Keep foreign addresses, AD and raw bit streams private. Publish only allowlisted
packet metadata, owned protected-PDU hashes, counts and source/decoder provenance.

Source-phase joins use every command-start through complete payload-receipt
bracket and the original one-second transition guards. Report packet observations
and excluded captures. No source-registration count, snapshot count, controller
zero field or receiver-hypothesis count becomes a transmitted denominator.

Implement and test through locked Nix and Task, commit the exact wrapper before
the corrected physical-data replay, and record the unchanged core decoder hash
plus the wrapper hash. Keep raw/private output in fresh ignored paths. A null
remains inconclusive; a corrected positive establishes decoding of those saved
waveforms, not fresh live acquisition, calibrated sensitivity, an Intel cause,
reliable three-pair RF response or counted-source acceptance. Conditional Trial B
still requires its separately declared live SDR-positive condition.
