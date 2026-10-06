# Controlled spectrum session 001: pre-declared protocol

Declared 2026-10-06, before any session 001 data exists. It covers spectrum
tasks 1.2, 2.1 and 2.2. Levels are relative ADC codes; no calibrated
reference exists.

## Common setup

- Same original ESP32, placement and antenna as the hit-rate runs.
- Preservation first: a fresh full 4 MiB read must equal the baseline. Then
  install the reviewed `550fade-uart921600` image.
- Capture: `esp_sdr_capture.py --batch-fsync`, 16 MS/s, 8-bit, 16,380 samples.
- Owned source: `ble_repeat_source_container.py --channel N` (extended,
  zero-data, 255-event controller-counted cycles at 20 ms).
- Restore the original image and verify it with a full readback before
  publishing.

## A. Source-on/off pairs at known channels (task 1.2)

| Channel | Centre | LO | BW | Gain |
| --- | --- | --- | --- | --- |
| 37 | 2402 MHz | 2401 MHz | 12 | hardware |
| 38 | 2426 MHz | 2425 MHz | 12 | hardware |
| 39 | 2480 MHz | 2479 MHz | 12 | hardware |

For each channel, one continuous capture runs while the source repeats three
times: 40 s off, then 10 counted cycles on. A 40 s off tail ends the capture.
Windows are classed ON/OFF with the 100 ms guard used by the hit-rate report.

Per pair, report:

- the ON-minus-OFF excess of a burst-gated spectrum (the strongest 1,024-sample
  block per window, averaged);
- the frequency of that excess's peak relative to the LO;
- owned ADV_EXT_IND decodes at a −1.8 MHz shift with `--accept-chsel`;
- background (OFF) power.

**Confirmed:** in all 3 pairs of a channel, the excess peak lies within 2 MHz
of the expected offset, which is +1 MHz plus the measured +0.8 MHz board
offset. **Not confirmed:** otherwise.

## B. Filter and gain sweep on a fixed input (task 2.1)

The channel-37 source stays on throughout, with LO 2401. Each condition takes
100 windows:

- BW 12, 20, 40 and 67 MHz with hardware gain;
- BW 20 with manual gain 16, 32, 48, 64 and 72.

Report for each condition:

- mean and 99th-percentile AC power;
- the fraction of components at the ADC endpoints (clipping);
- burst-gated spectrum width;
- the frequency of the carrier peak;
- owned decodes.

## C. Extended tuning against an independently known signal (task 2.2)

The reference is the FM station at 101.1 MHz. The RTL-SDR independently records
its spectrum immediately before the ESP captures.

ESP captures (BW 12, hardware gain, 60 windows each). The firmware tunes in
1 MHz steps (`RANGE 100 6000 1`; this amendment was made before any data
existed). Captures at:

- LO 100 MHz;
- LO 102 MHz (99 MHz is below the firmware's 100 MHz minimum);
- LO 106 MHz as a control;
- LO 100 MHz again with manual gain 48.

**Confirmed point:** the strongest narrow peak appears at about +1.1 MHz at
LO 100 and moves to about −0.9 MHz at LO 102, within two 15.6 kHz FFT
bins plus the measured board offset scaled to that frequency. Other stations in
the RTL-SDR view may appear too, but the 101.1 peak must track the LO.
**Rejected:** a peak that doesn't move with the LO (spur or alias), or no peak.
The in-band points are channels 37, 38 and 39 from part A. No other extended
point is claimed.

## Stop conditions

Stop on any capture fault, then restore and verify the original image. No
automatic retry. Every condition's raw IQ stays private under `.scratch/`.
