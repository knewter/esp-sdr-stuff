# First Task-launched ESP spectrum trial: failed acquisition, verified recovery

Physical run on 2026-10-02 using the Nix-built receiver candidate, the identified
preserved ESP32 and the reviewed `demo:esp` Task command. The requested profile
was 60 seconds, 2412 MHz, nominal 80 MS/s, 512 FFT bins, 20 MHz requested filter,
hardware AGC and 921600 baud.

The reader accepted 205 spectrum frames before reporting a spectrum CRC
mismatch. Its last accepted frame arrived 1.72658 seconds after acquisition
began. There is no firmware end report and the 60-second gate **fails**. The
failed trial remains separate from any later successful candidate. Both
artifacts have identical executable segments according to the subsequent
binary comparison; this trial does not identify the cause of the transport
failure or establish a compiler regression.

- [Demo lifecycle and exact installed part hashes](demo.json)
- [Fresh current-flash comparison](before-install.json)
- [Failed acquisition settings and classification](spectrum.json)
- [Accepted frame timing and numerical metrics](spectra.csv)
- [Actual failed browser display](completed-spectrum.png)
- [Independent full-flash readback and original boot flags](restoration.json)
- [Independent replay and recovery review](../esp-demo-independent-review/README.md)

The rejected corrupt frame was not saved by the original reader. Independent
replay checks every retained accepted frame and its CRC, sequence and metrics;
it cannot independently reproduce the recorded rejection from absent bytes.
The screenshot shows the failed live hardware session; it proves the display,
while the retained private frame prefix proves accepted-frame integrity.
The failure occurred before the five-second live screenshot trigger.

Cleanup confirms the owned UART worker exited before recovery. Restoration
writes the preserved image, independently rereads all 4,194,304 bytes and
matches SHA-256 `6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`.
The original application, SDK and both GPIO states are observed after reset.
This is verified recovery from this failed trial, not a new physical power-cycle
claim. Private frames, raw logs and full flash reads remain ignored and protected.

Executed command, with local private paths retained outside the public receipt:

```sh
nix develop --command task demo:esp -- \
  --artifact .scratch/nix-firmware-check-v2/firmware \
  --manifest .scratch/nix-firmware-check-v2/firmware/manifest.json \
  --output docs/evidence/esp-demo-session-001 \
  --private .scratch/esp-demo-session-001 --headless
```

Task returned failure (201); the underlying demo returned 2. No RF calibration,
known-packet decode, continuous RF coverage or FPGA result is inferred.
