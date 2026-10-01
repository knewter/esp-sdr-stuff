# ESP32 physical evaluation tools

These tools are for the pinned ESPARGOS original ESP32 protocol-6 firmware.
Only one operator may own the board. Finish flash preservation before use.
`pyserial` and `numpy` are required; no device is opened by module imports or tests.
The default stable CP2102 path is verified against USB VID/PID before opening,
and DTR/RTS are held inactive. Each physical operation closes its handle.

## Snapshot integrity and timing

From the repository root, use a fresh output directory and a separate ignored
raw directory:

```sh
python3 tools/esp_sdr_capture.py \
  --output docs/evidence/snapshot-baseline \
  --private .scratch/snapshot-baseline-raw \
  --count 100 --samples 16380 --bits 8 10 \
  --rates 16000000 40000000 80000000 \
  --frequency 2412 --bandwidth 20 --gain hardware
```

This collects 100 attempts for each of six rate/precision combinations,
independently checks zlib/IEEE CRC32 and sample counts, preserves per-attempt
CSV timestamps and anonymous code statistics, and saves raw payloads privately.
Failures remain failures in the CSV; they are not silently replaced by retries.
Exit 2 means the required count of successful captures was not reached.

Timing uses host monotonic timestamps. A command interval is not a precise
hardware start interval. Coverage sums nominal sample windows divided by wall
time and does not establish independently calibrated sample clocks or exact
missed-event counts. Firmware capture time includes polling/overhead.

Settings can be changed for controlled source-on/source-off and gain/filter
experiments. Host statistical power is measured in squared ADC code units,
not dBm. This harness does not identify or decode Wi-Fi networks and publishes
no raw payload or network names. No controlled-signal conclusion can be drawn
from an anonymous noise-only series.

## Browser spectrum through an explicit UART bridge

```sh
python3 tools/esp_sdr_spectrum_bridge.py \
  --output docs/evidence/spectrum-browser \
  --private .scratch/spectrum-browser-raw \
  --seconds 60 --rate 80000000 --bins 1024 \
  --frequency 2412 --bandwidth 20
```

Open `http://127.0.0.1:4340` and click **Start bounded trial**. The host opens
the real CP2102 UART, streams on-device snapshot FFT frames, validates each
CRC/shape/index, saves raw frames privately and numerical frame CSV publicly,
and releases UART after the bounded trial. The browser displays actual frames
and can be captured at 10/30/60 seconds with Playwright. Results are written on
completion or failure. Stop the HTTP process when finished.

This is **localhost HTTP plus a host UART reader**, explicitly labeled in the
viewer and metadata. It is not direct browser Web Serial and does not validate
the upstream ESPARGOS viewer. It provides a reproducible browser spectrum
session without requiring a browser serial chooser or trusting a moving web app.
All frames are separate acquisitions with gaps; the viewer labels the snapshot
gap flag and nominal coverage. Its Y axis is firmware power code, uncalibrated.

## Host verification

```sh
python3 -m unittest discover -s tests -p test_esp_sdr_capture.py -v
```

Synthetic parser tests cover fragmented binary delivery, embedded newline
bytes, CRC mismatch, short transfer, sample mismatch, signed 8-bit and odd
10-bit packing, FFT framing and retained nonzero end status. These prove host
parser behavior only; physical tasks require the resulting hardware evidence.
