## 1. Measure event observation

- [ ] 1.1 Define a repeatable owned source with at least 100 counted emissions and documented duration/bandwidth; check the selected capture window can fit it.
- [ ] 1.2 Record captures and compute hits, complete bursts, misses and uncertainty relative to source ground truth.

## 2. Evaluate a bounded decoder

- [x] 2.1 Choose a decoder for an actually captured, complete waveform and document its input format; verify a known payload rather than visual resemblance. Proof: [four independently replayed packets](docs/evidence/ble-owned-decoding/README.md) and [10-bit example](docs/evidence/ble-controls-decoding/README.md).
- [x] 2.2 Publish the capture/decoder manifest, summary plots and application matrix with useful/limited/not-demonstrated outcomes. Proof: [manifests, amplitude plots and application matrix](docs/evidence/ble-owned-decoding/README.md), [control-sweep manifest](docs/evidence/ble-controls-decoding/README.md).

The five packets verify their protected PDUs and exact owned AD, with complete
packet windows inside the captures. They do not establish 100 emitted events,
missed-event rates or reliable detection in three repetitions. The first two
tasks remain open; registration counts and snapshot counts are not emissions.

[The predeclared accounting tool](docs/research/ble-counted-trials.md) is ready,
but [three finite source-only diagnostics](docs/evidence/ble-counted-source-smoke/README.md)
produced no actual termination counter. Their accepted requested limits do not
close task 1.1 or supply input to task 1.2. Keep the three receiver trials pending
until the independent source-count gate passes.

## Proof procedure

Physical proof: 100 counted emissions plus capture timestamps and a saved waveform; offline proof: run the selected decoder on the pinned capture and compare output to the known payload. No decoder or protocol support is assumed in advance.

Required outcome: At least 100 deliberately emitted repeat events with ground-truth counts and capture hit rate; a decoding claim includes a complete waveform and verified payload.

## Subsequent diagnostic checkpoint

The [single reachable legacy100 count diagnostic](docs/evidence/ble-count-limit-100-001/README.md)
also retains actual `0x3c/count0`, with [independently verified cleanup](docs/evidence/ble-count-limit-100-independent-review/README.md).
It supplies no usable emitted denominator. A separately prospective
[extended100 source-only condition](docs/research/ble-extended-count-limit-100-protocol.md)
cannot qualify the original legacy255 reports or close either event-observation task.

The [actual extended100 report](docs/evidence/ble-extended-count-limit-100-001/README.md)
does observe controller count100, but the full monitoring lifecycle fails.
Neither its auxiliary-channel payload nor that failed episode supplies the
original legacy marker denominator. Original event-observation tasks stay open.

[Timer source diagnostics](docs/evidence/ble-duration-source-diagnostics/README.md)
observe termination events with actual count zero. The [ten-episode RF
discriminator](docs/evidence/ble-zero-counter-rf/README.md) preserves 262
snapshots but yields no CRC-valid owned packet. Its null result is inconclusive,
and its scheduling deviation remains recorded. These diagnostics establish no
≥100-event denominator, hit rate or task 1.1/1.2 acceptance.

The [independently replayed advertising-mode pair](docs/evidence/ble-mode-counter-independent-review/README.md)
accepts ten source commands and verifies both original source/monitor
terminations. Legacy and extended modes both retain `0x3c/count0` with
complete cleanup. Their count gates remain failed; this supplies no emitted
denominator, fresh hidden-SDR packet or closure of task 1.1/1.2.

The [independently reviewed matched gain controls](docs/evidence/ble-matched-gain-independent-review/README.md)
reproduce one fresh complete owned packet in manual ten-bit capture 48 and
retain zero owned packets in the hardware-gain condition. All 1,994 transport
records, source cleanup and full restorations pass. No emitted denominator or
three-response result follows, and tasks 1.1/1.2 stay unchecked.
