## 1. Measure event observation

- [ ] 1.1 Define a repeatable owned source with at least 100 counted emissions and documented duration/bandwidth; check the selected capture window can fit it.
- [ ] 1.2 Record captures and compute hits, complete bursts, misses and uncertainty relative to source ground truth.

## 2. Evaluate a bounded decoder

- [ ] 2.1 Choose a decoder for an actually captured, complete waveform and document its input format; verify a known payload rather than visual resemblance.
- [ ] 2.2 Publish the capture/decoder manifest, summary plots and application matrix with useful/limited/not-demonstrated outcomes.

## Proof procedure

Physical proof: 100 counted emissions plus capture timestamps and a saved waveform; offline proof: run the selected decoder on the pinned capture and compare output to the known payload. No decoder or protocol support is assumed in advance.

Required outcome: At least 100 deliberately emitted repeat events with ground-truth counts and capture hit rate; a decoding claim includes a complete waveform and verified payload.
