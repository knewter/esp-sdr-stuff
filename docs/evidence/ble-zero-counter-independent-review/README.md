# Independent replay: zero-counter RF result remains inconclusive

Read-only review, 2026-10-02 UTC. Independently replayed **all 262 private
waveforms**, including the 42 supplemental OFF captures, after root confirmed
original-firmware restoration. The pinned blind decoder found **zero
CRC-valid owned or foreign packets**. Main capture 114 contains one AA candidate
with failed CRC; it establishes no owned reception. The complete decoded frame
results match the published manifests, and a separate execution of the final
reporter produced an analysis identical to the author's.

This is an **inconclusive diagnostic**, not proof of no RF emission or a
controller defect. The continuous-tail requirement failed. No recorded-source
denominator, hit rate, ≥100 counted-event acceptance or new physical-task
completion follows from this experiment.

## Reviewed provenance and integrity

Physical receipts originate at `1cfc291c38ab6d76388db0bb5f12c7d7ead5f496`;
the final reporter/replay checkpoint reviewed is author
`3693fe75b9ad083310cf734a3cde7fa1df2db442`, integrated on root as
`ca26f68`. Reviewed script SHA256 values:

- Source: `5628261cff21b3220d66842d347d88c5a6800c7770b99f596ef54a2f759625cc`.
- Decoder: `834fdd78e3221d0625eaa7cf1059b9bd59d3b8b9fa929578f2555bff64130128`.
- Final reporter: `085991f8c9ea172dfe7a5b08379eea42e1d8995b54796564a511f9e43c3409c0`.
- Retained acquisition supervisor:
  `fb7d3e9b076040a74b409fe62d910f25cc7c6ffac6eff4335148772e2be0233a`.

Recomputed all **55** file hashes in the physical provenance manifest and all
**12** files in the separate source-only duration receipt. All matched. Actual
source, decoder, monitor and receiver tool hashes match their recorded pins.
Every waveform independently matches its CSV and decoder SHA256, byte length,
transport CRC and 16,380-pair count: **8,583,120 bytes / 4,291,560 complex
pairs**, with 262 distinct waveform hashes. Both capture segments retain their
original local index sequence. Receiver settings and actual setting
acknowledgements match LO 2401 MHz, filter 20 MHz, gain 48, nominal 16 MS/s and
8-bit components. No raw IQ, addresses or foreign payloads are published here.

See [numerical checks](numerical-checks.json),
[physical receipts](../ble-zero-counter-rf/provenance.json),
[final analysis](../ble-zero-counter-rf/analysis.json), and the
[committed prospective protocol](../../research/ble-zero-counter-rf-protocol.md).

## Source, monitor and schedule

All ten native episodes and the independent monitor agree on handle 1,
properties `0x10`, channel map 1, LE1M, 20 ms interval, exact owned AD,
five-second duration and requested MaxEvents 255. Each delivered a matching
termination with **status `0x3C` / controller count 0**, followed by successful
handle-specific disable/removal and socket closure. All five command
acknowledgements per episode have status zero. Original `trial_failed` and exit
2 are preserved; requested 255 supplies no denominator. Pre/post BlueZ checks
retain powered=true, discovering=false and ActiveInstances=0.

The native `command_sent` rows omit duration/maximum fields. The native
`source_enabled` fields and monitor wire-command sets verify those values;
the omitted fields were not reconstructed into the original transcripts.
The completed monitor retains 136 packets / 110 sanitized controls covering
all episodes. Its readiness before receiver startup has procedural supervisor
and log evidence, not a separate monotonic READY timestamp. Monitor loss remains
unmeasured; host brackets are not hardware RF timestamps.

Using the whole command-through-payload bracket, both readers' conservative
enable/termination times, and 100 ms guards gives **125 source snapshots**:
13, 12, 13, 12, 12, 13, 12, 13, 12, 13 across episodes 01–10.
The remaining captures are **108 OFF / 29 boundary**. Independent accounting
matches the published phase results. All inter-episode OFF gaps exceed one
second; the only failed CRC candidate falls in guarded episode 06.

Recomputed baseline: **5.658143615 s**. Initial post-cleanup tail:
**8.620009836 s**, failing the required >10 s continuous tail. The separate
42-capture supplement begins after a **54.217849097 s gap** and spans
**15.316331917 s**. It supplies additional OFF observations; it does not repair
continuous schedule compliance. No waveform or failed schedule was omitted.

## Reporter safeguards and restoration

Independently reran all **10 diagnostic regression cases**, passing. Reviewed
fixes require the source hash, actual receiver setting acknowledgements,
matching native/monitor configuration and cleanup, episode order/OFF gaps,
baseline, exact bounded search, full packet-window proof, finite consistent
bounds, protected-PDU hash and explicit refined periods. Coarse slicing is
exactly four samples per symbol. Duplicate hypotheses collapse; conflicting
owned clusters are rejected in source, OFF and boundary captures. Missing
positive metadata cannot become a verified reception. The final generated
analysis keeps RF event count and reception rate null and counted acceptance
false.

Independently read the private restored **4,194,304-byte** image: SHA256
`6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`,
matching original preservation; file mode is 0600. Reviewed write verification,
full readback and fresh hello_world / ESP-IDF v5.4-dirty / 160 MHz reset boot in
[restoration evidence](../zero-counter-restoration/README.md). The image header
still declares 2 MiB while the detected device has 4 MiB, matching the
preserved original behavior. Electrical power removal and cold recovery remain
unverified. This reviewer opened no serial, USB or Bluetooth device.
