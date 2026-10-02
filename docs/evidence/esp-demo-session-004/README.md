# Fresh Nix artifact: retained eight-window CRC failure

Physical trial on 2026-10-02. This used the freshly Nix-built UART921600
artifact with the eight-window profile that completed
[session 003](../esp-demo-session-003/README.md). The receiver executable
segments match the historical artifact; exact descriptor and footer bytes
[differ](../esp-firmware-comparison/README.md). The viewer also carries the
reviewed terminal-timing correction recorded by its executed tool hash.
This is a separate physical evaluation, not inherited proof of the new binary.

The accepted prefix contains 1,780 CRC-valid, consecutive spectrum frames
and 14,240 FFT windows. Acquisition failed a spectrum CRC check after
45.616564 seconds. There is no successful firmware end report; the requested
60-second gate **fails**. The consumed rejected frame is retained privately,
and its size, SHA-256 and mismatching CRC values are public.

Frame-arrival timestamps show a 6.165-second host gap before sequence 1772,
followed by eight accepted frames through sequence 1779. The next rejected
544-byte record begins with sequence 1780 and contains another plausible
`SPC1` header at byte 322, with sequence 2050. These observations support
investigating receive stalls and byte loss. They do not identify the component
responsible or prove a firmware, USB bridge, filesystem or host scheduler fault.
The synchronous raw-frame file writes are a candidate for a bounded follow-up;
changing storage and UART baud together would confound that trial.

- [Exact receiver part hashes and lifecycle](demo.json)
- [Independent original-flash check before installation](before-install.json)
- [Failed capture, accepted prefix and rejected-frame metadata](spectrum.json)
- [Per-frame integrity and arrival timing](spectra.csv)
- [Actual live display](live-spectrum.png)
- [Actual failed terminal display](completed-spectrum.png)
- [Full restored readback and matching original reset boot](restoration.json)
- [Independent review](../esp-demo-independent-review/README.md)

The owned UART process group was confirmed closed before restoration. All
4,194,304 restored flash bytes match the preserved original SHA-256, and the
original application, SDK and both GPIO states were observed at reset boot.
This is verified recovery from a failed trial; no electrical power-cycle claim
is made. Exact payloads, full flash images, identifiers and raw logs stay private.

```sh
nix develop --command task demo:esp -- \
  --artifact .scratch/nix-firmware-check-v2/firmware \
  --manifest .scratch/nix-firmware-check-v2/firmware/manifest.json \
  --ffts-per-frame 8 \
  --output docs/evidence/esp-demo-session-004 \
  --private .scratch/esp-demo-session-004 --headless
```

Task returned 201; the underlying demo returned 2. The earlier complete minute
remains a valid bounded result, while dependable repeatability, calibrated RF,
counted burst reception and FPGA transport remain unproven.
