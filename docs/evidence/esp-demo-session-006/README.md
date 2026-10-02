# Second consecutive Nix-built RAM-buffered spectrum minute

Physical run on 2026-10-02. The exact same Task command, installed firmware,
921600 baud, 2412 MHz, nominal 80 MS/s, 512 bins, 20 MHz filter, hardware AGC,
eight-window grouping and RAM-buffered bridge repeat [session 005](../esp-demo-session-005/README.md).
No settings or source changes were made between these two runs. Task and the
underlying demo both return 0.

| Check | Physical result |
| --- | --- |
| Spectrum / statistics frames | 2,713 / 226; all CRC-valid |
| FFTs / processed pairs | 21,704 / 11,112,448; matching end totals |
| Host / firmware duration | 60.003268 s / 60.003178 s |
| Nominal coverage | 0.231497%; reception windows contain gaps |
| Accepted stream | 1,484,912 bytes; saved bytes independently verified |
| Full original flash / reset boot | 4,194,304 bytes match baseline; all known boot flags pass |

This is the second consecutive completed minute with the recommended Nix-built
profile and current bridge. It demonstrates these bounded repetitions; it does
not establish a long-run reliability rate or prove a cause for the earlier
receive stalls. Both actual viewer images label temporal averaging, nominal
sampling and uncalibrated power. Buffered data is saved after closing the UART.

- [Exact installed hashes and lifecycle](demo.json)
- [Current original-flash check](before-install.json)
- [Counts, settings, persistence hash and end totals](spectrum.json)
- [Per-frame metrics](spectra.csv)
- [Actual live display](live-spectrum.png)
- [Actual completed display](completed-spectrum.png)
- [Independent full-flash restoration and matching reset boot](restoration.json)
- [Independent review](../esp-demo-independent-review/README.md)

```sh
nix develop --command task demo:esp -- \
  --artifact .scratch/nix-firmware-check-v2/firmware \
  --manifest .scratch/nix-firmware-check-v2/firmware/manifest.json \
  --ffts-per-frame 8 \
  --output docs/evidence/esp-demo-session-006 \
  --private .scratch/esp-demo-session-006 --headless
```

Exact RF frames, full flash images, device identifiers and raw logs remain private.
The three earlier failures and historical success remain recorded. Software reset
recovery is distinguished from electrical power cycling. No calibrated RF,
counted BLE reliability, continuous reception or FPGA transport gate closes.
