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

## Classic CP2102 needs a 1 Mbaud firmware variant

Upstream firmware defaults to 2 Mbaud. The Linux driver clamps a classic
CP2102 to 1 Mbaud, so requesting 2 Mbaud in pyserial does not establish a
2 Mbaud physical UART. The host tools now reject a mismatched kernel termios
speed instead of waiting for garbled protocol replies.

Use the local pinned configuration variant with **`--baud 1000000`** for both
snapshot capture and the browser bridge. The source revision is unchanged;
record `--firmware-revision 550fade-uart1m` for snapshot installation provenance.
The variant changes the Kconfig transport default only, and sets the application
version to make that change visible at boot.

To reproduce it, clone ESPARGOS revision
`550fadea4d00a9e26ce921c5832167becb3dc20c` and ESP-IDF revision
`25fe69f946311abdaf9ad56591f25fedbc20ac98`, initialize both repositories'
submodules, install the SDK's ESP32 tools and Python environment, and activate
its `export.sh`. Then:

```sh
python tools/build_esp_sdr_uart.py \
  --source .scratch/esp-sdr --sdk .scratch/esp-idf \
  --build .scratch/build-esp32-uart1m \
  --output .scratch/firmware-esp32-uart1m \
  --evidence docs/evidence/firmware-uart1m \
  --baud 1000000 --jobs 6
```

The build wrapper rejects wrong source/SDK revisions and tracked modifications,
uses a fresh build/configuration, confirms target/CPU/UART config, exports the
upstream-compatible flash manifest, and records compiler/configuration hashes.
It never flashes a device. Binary downloads, SDK and build output stay ignored.

Primary driver reference: [Linux cp210x driver](https://github.com/torvalds/linux/blob/master/drivers/usb/serial/cp210x.c),
`cp210x_init_max_speed` (classic CP2102/CP2103 maximum 1,000,000; CP2102N
maximum 3,000,000) and `cp210x_change_speed` (clamps requests to the maximum).
The physical board's accepted speed must still be checked; product strings
alone do not prove which bridge revision is installed.
