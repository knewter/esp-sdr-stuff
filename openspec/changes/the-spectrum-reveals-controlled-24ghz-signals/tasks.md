## 1. Define controlled inputs

- [ ] 1.1 Inventory the source/reference/attenuator equipment; write settings and known limits before collecting RF data.
- [ ] 1.2 Record at least three repeated source-on/source-off pairs at known 2.4 GHz channels; compare tone/channel location and background.

## 2. Measure receiver limits

- [ ] 2.1 Sweep advertised filters and gain on a fixed input; record spectra, center offset and clipping indicators.
- [ ] 2.2 Test each proposed extended-tuning point against a known reference signal; reject alias-only or unconfirmed points.
- [ ] 2.3 Publish plots, source settings and uncertainties, and decide the band/window settings usable for later experiments.

## Proof procedure

Physical procedure: fixed source, fixed antenna placement, paired on/off captures, three repeats per condition. Future plot harness consumes the saved capture manifest and CSV; raw acceptance is based on the known-source shift and repeated response, not just an OK command.

Required outcome: Three repeatable source-on/source-off pairs with known center frequencies; each claimed extra tuning point has an independently known signal and uncertainty.
