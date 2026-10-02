# Historical-artifact Task demo: retained CRC failure

Physical trial on 2026-10-02. This used the identical host workflow and receiver
settings as [trial 001](../esp-demo-session-001/README.md), changing only the
installed artifact to the previously successful UART921600 image. It accepted
4,965 spectrum frames, with the final accepted frame at 41.521749 seconds, then
reported a spectrum CRC mismatch. It has no successful firmware end report;
the requested 60-second acquisition gate **fails**.

The receiver binaries differ in descriptor/footer bytes, while their executable
segments match. This comparison does not locate the cause of either CRC failure.
The next planned intervention increases FFT windows averaged per emitted frame
from one to eight to reduce the UART output load; its success is not assumed.

- [Exact installed hashes and lifecycle](demo.json)
- [Current original-flash check](before-install.json)
- [Failed acquisition classification](spectrum.json)
- [Accepted frame metrics](spectra.csv)
- [Actual display during the trial](live-spectrum.png)
- [Actual failed terminal display](completed-spectrum.png)
- [Fresh full-flash readback and matching original boot](restoration.json)
- [Independent review](../esp-demo-independent-review/README.md)

Both screenshots display actual hardware spectra with snapshot gaps and
uncalibrated power codes. They prove the viewer; numerical/private frame replay
establishes accepted-frame integrity. The existing reader did not retain the
rejected corrupt frame, so offline replay cannot reproduce that rejection.

The owned UART worker is confirmed closed before restoration. A fresh independent
4,194,304-byte read matches the preserved original image and its SHA-256, and all
known original application/SDK/GPIO reset-boot observations pass. This is verified
recovery from a failed capture, not a new physical power-cycle observation.

```sh
nix develop --command task demo:esp -- \
  --artifact .scratch/historical-uart921600 \
  --manifest .scratch/historical-uart921600/manifest.json \
  --output docs/evidence/esp-demo-session-002 \
  --private .scratch/esp-demo-session-002 --headless
```

Task returned 201; the underlying demo returned 2. No successful minute, calibrated
RF, continuous reception, packet count or FPGA result is claimed.
