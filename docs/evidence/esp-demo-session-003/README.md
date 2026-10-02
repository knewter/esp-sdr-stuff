# Successful Task-launched ESP spectrum demonstration

Physical run on 2026-10-02. The documented Nix-backed `demo:esp` command
installs the verified UART receiver, starts the same local viewer, records the
bounded acquisition, closes its UART worker and restores the original image.
Task and the underlying demo both returned success.

The measured profile uses the historical UART921600 artifact, 2412 MHz,
nominal 80 MS/s, 512 FFT bins, 20 MHz requested filter, hardware AGC and **eight
separately acquired FFT windows averaged per emitted frame**. These are separate
windows with gaps; averaging does not create continuous reception.

| Check | Physical result |
| --- | --- |
| Spectrum frames | 2,709, all CRC-valid and consecutive |
| Statistics frames | 225, all CRC-valid |
| FFTs / processed pairs | 21,672 / 11,096,064, matching firmware end totals |
| Host duration / firmware duration | 60.022283 s / 60.019182 s |
| Nominal sampled time / coverage | 0.1387008 s / 0.231082% |
| Accepted streamed frame data | 1,482,696 bytes, about 24.70 kB/s across this interval |
| Restored flash | All 4,194,304 bytes independently match preservation |
| Reset boot | Original application, SDK and both GPIO states observed |

Both initial one-window trials failed CRC and remain recorded:
[trial 001](../esp-demo-session-001/README.md) and
[trial 002](../esp-demo-session-002/README.md). Compared with trial 002, this
trial changes FFT units per emitted frame from one to eight; source/firmware
artifact, UART baud, bins and RF settings stay the same. The measured lower
streamed-byte rate and this passing minute support the profile for the demo.
They do not locate the original corruption mechanism, guarantee long-run
reliability or establish a causal improvement from one trial alone.

- [Lifecycle and exact receiver part hashes](demo.json)
- [Actual original-flash check before installation](before-install.json)
- [Frame counts, settings, duration and firmware end totals](spectrum.json)
- [Per-frame CRC, sequence, gain, timing and power metrics](spectra.csv)
- [Actual live browser display](live-spectrum.png)
- [Actual completed browser display](completed-spectrum.png)
- [Full restored readback and original reset boot](restoration.json)
- [Independent frame/artifact/recovery replay](../esp-demo-independent-review/session-003-checks.json)
- [Independent review](../esp-demo-independent-review/README.md)

The screenshots prove the displayed physical session. The terminal screenshot's
elapsed field is the last received frame time, approximately 59.979 s;
completion is established by the recorded host interval and textual firmware
end report, both above 60 s. Private CRC-bearing frames independently reproduce
every public row and aggregate. The textual end report has no CRC of its own;
its live-validated recorded scalars match those independent aggregates.

Full flash reads, raw boot output, device identifiers and exact frame payloads
remain private. Recovery uses a reset boot; this run does not independently
prove a physical power cycle. Power codes are uncalibrated, the ADC clock is
nominal, and no signals are identified from the spectrum alone. This minute
closes no calibrated RF, counted-burst reliability or FPGA transport gate.

Executed physical proof command:

```sh
nix develop --command task demo:esp -- \
  --artifact .scratch/historical-uart921600 \
  --manifest .scratch/historical-uart921600/manifest.json \
  --ffts-per-frame 8 \
  --output docs/evidence/esp-demo-session-003 \
  --private .scratch/esp-demo-session-003 --headless
```

Use fresh output names when repeating the command, and omit `--headless` to
open the interactive viewer and press Start. The separate `demo:esp:restore`
Task command provides independently verified recovery. The [offline segment comparison](../esp-firmware-comparison/README.md)
finds identical executable code in the fresh Nix-built artifact, but its eight-window profile still
needs a separate physical trial before claiming that exact binary was verified.
