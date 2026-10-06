# C3 burst session 001: pre-declared protocol

Declared 2026-10-06, before any session data exists. It asks whether the
ESP32-C3 receiver ([first contact](../evidence/esp32c3-receiver/README.md))
sees the controller-counted BLE source on channel 37.

## Why bursts, not packets

The C3 build captures only at 80 MS/s, so a 16380-sample snapshot covers
204.75 µs. An owned packet lasts 184 µs and arrives about every 24.7 ms. A
**complete** packet fits only when it starts in a 20.75 µs slack, about 0.08%
of windows. Some **part** of a packet overlaps about 1.6% of windows. So the
primary test counts narrowband burst energy. The packet decoder still runs,
and its results are reported only.

## Setup

- **Receiver:** ESP-SDR `550fade` built for esp32c3 with
  `CONFIG_ESP32C3_REV_MIN_2=y`, on UART0 through the CP2102N at 2 Mbaud. The
  board's original image is preserved and verified in ignored
  `backups/esp32c3/`.
- **Capture settings:** LO 2396 MHz, bandwidth 40, hardware gain, 8-bit,
  80 MS/s, 16380 samples. Channel 37 (2402 MHz) sits 6 MHz above the LO.
- **Source:** the counted extended-advertising source on channel 37
  (`tools/ble_repeat_source_container.py`, 255 events per cycle at 20 ms).

## Captures

Three pairs. Each is one capture of 600 windows (about 190 s at the measured
317 ms per window). Its source container starts 40 s after the capture and
runs 15 counted cycles (about 96 s). The rest of the capture is OFF.

## Analysis

`tools/c3_burst_detect.py`, fixed before the run:

- 64-point FFT frames smoothed over 20 µs;
- per-window AGC scaling from 2380–2392 MHz;
- per-bin capture-median reference;
- search band 2399–2409 MHz;
- detection needs at least 10 dB over the reference **and** at least 6 dB
  over both bands 4–6 MHz to either side (rejects Wi-Fi).

ON and OFF windows use 100 ms guards around the counted source spans. On 20
source-off smoke windows, the detector made no detections; the highest peak
was 5.3 dB.

**Confirmed:** every pair has at least one ON detection, and over all pairs ON
detections exceed OFF detections with a one-sided Fisher exact p < 0.01. ON
detection frequencies are reported as a location estimate. **Not confirmed:**
otherwise, reported as is.

Also reported: `tools/ble_extended_primary.py --rate 80000000` with
`--accept-chsel` over a translation grid from −6.0 to −9.0 MHz in 0.4 MHz
steps. This counts complete owned packets; at most a few are expected.

## Stop conditions

On a capture fault, keep the completed captures and skip the rest. No retry.
The C3 keeps the ESP-SDR image afterwards. Its original image can be restored
from the backup on request.
