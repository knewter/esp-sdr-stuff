# Fresh Nix firmware completes the RAM-buffered spectrum minute

Physical run on 2026-10-02. The documented `demo:esp` Task completed using
**the exact fresh Nix-built UART921600 receiver artifact**: 2,712 valid
spectrum frames over 60.009361 host seconds and 60.009198 firmware seconds.
Task and the underlying demo returned 0. All 4,194,304 original flash bytes
were independently reread after restoration and match preservation; the known
original application, SDK and both GPIO states were observed at reset boot.

| Recorded quantity | Physical result |
| --- | --- |
| Spectrum / statistics frames | 2,712 / 226; all CRC-valid |
| FFT windows / processed pairs | 21,696 / 11,108,352; matching firmware end totals |
| Host / firmware duration | 60.009361 s / 60.009198 s |
| Nominal sampled time / coverage | 0.1388544 s / 0.231388% |
| Retained accepted binary stream | 1,484,368 bytes, independently verified after saving |
| Largest consecutive host frame-arrival gap | 0.0278601 s |
| Stream SHA-256 | `6eba61aa8478c80b9905baafb98af0814e4bc3f97369b7c4a359eb161669726b` |

Relative to the failed [fourth trial](../esp-demo-session-004/README.md),
the installed binaries, 921600 baud, LO 2412 MHz, nominal 80 MS/s, 512 bins,
20 MHz requested filter, hardware AGC and eight-window grouping stay fixed.
The host now retains CRC-checked frames in a bounded RAM buffer and writes
and independently verifies them **after closing the UART**. Its executed
bridge is `e8c39db4f8e621011a7a92192f62246219604903e1a629aa899107cf1b880608`.
[Independent code/host review](../esp-demo-independent-review/ram-retention-review.json)
checks the cap, post-closure persistence, slow-writer and failure behavior.

This passing trial supports the changed workflow; it does not establish the
component responsible for the earlier receive stalls or a long-run failure rate.
Each update averages linear power from eight separately acquired FFT windows.
The windows contain gaps, the sample clock is nominal and power codes are
uncalibrated. RAM retention also means forced process or host loss before saving
can lose those buffered bytes. Normal protocol, cap and persistence failures
remain explicit failures with available private evidence retained.

- [Lifecycle and exact receiver part hashes](demo.json)
- [Actual original-flash check before installation](before-install.json)
- [Frame integrity, settings, timing and firmware end totals](spectrum.json)
- [Per-frame sequence, gain, CRC and arrival metrics](spectra.csv)
- [Actual live viewer](live-spectrum.png)
- [Actual completed viewer](completed-spectrum.png)
- [Full restored readback and matching original reset boot](restoration.json)
- [Independent physical replay](../esp-demo-independent-review/README.md)

```sh
nix develop --command task demo:esp -- \
  --artifact .scratch/nix-firmware-check-v2/firmware \
  --manifest .scratch/nix-firmware-check-v2/firmware/manifest.json \
  --ffts-per-frame 8 \
  --output docs/evidence/esp-demo-session-005 \
  --private .scratch/esp-demo-session-005 --headless
```

Use fresh destination names when repeating and omit `--headless` for the
interactive Start button. Full flash images, exact RF payloads, device identifiers
and unsanitized logs remain private. Reset recovery is distinguished from
physical power cycling. The earlier historical-artifact success and all three
new failed trials remain recorded; no RF calibration, signal identification,
counted-burst reliability or FPGA transport gate closes from this minute.
