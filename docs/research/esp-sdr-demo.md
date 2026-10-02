# Repeatable ESP32 spectrum demo

The demo command installs a verified ESPARGOS receiver, opens a local live spectrum viewer, records a bounded session, and restores the preserved original firmware. It is for the identified original ESP32 behind the CP2102 bridge. One operator owns that device throughout. The dual-serial ACM device belongs to another project.

The [third physical demo session](../evidence/esp-demo-session-003/README.md) completed 60.022 seconds with 2,709 CRC-checked frames, eight separately acquired FFT windows per frame and matching end totals. All 4 MiB of restored flash matched the original baseline, followed by its expected reset boot. This is one successful bounded profile, with reception gaps and no electrical power-cycle claim. Host tests exercise synthetic fixtures, including a real Nix Chromium canvas; those tests establish software behavior separately.

## Run the demo

Enter the repository and use the locked Nix environment. A prepared private UART-only firmware directory must contain `esp32/`, `manifest.json`, and `build-info.json`. The receiver source must be `550fadea4d00a9e26ce921c5832167becb3dc20c`, its SDK source `25fe69f946311abdaf9ad56591f25fedbc20ac98`, and its only receiver configuration change the matching UART default. The tool checks provenance, flash layout, every part's size and SHA-256 before an installation attempt; `flash_trial.py` repeats its existing security and artifact checks.

The successful session used the verified historical UART-only artifact prepared locally below. It is private and is not downloaded by this command. Choose new evidence and private directory names on each run:

```sh
nix develop --command task demo:esp -- \
  --artifact .scratch/historical-uart921600 \
  --manifest .scratch/historical-uart921600/manifest.json \
  --output docs/evidence/esp-demo-next \
  --private .scratch/esp-demo-next
```

The command prints its owned localhost URL and opens an isolated Chromium window. Press **Start bounded trial**. The default is 60 seconds at 2412 MHz, nominal 80 MS/s, 512 FFT bins, **eight FFT windows averaged per update**, hardware AGC and 921600 baud. Keep the terminal open while restoration completes. `--ffts-per-frame 1` reproduces the original one-window grouping. That grouping previously completed a physical 512-bin session but subsequently failed CRC in both new demo trials; the prior 1024-bin CRC failure remains separate. The eight-window session completed; it establishes that bounded outcome, rather than a general reliability rate. Earlier failed sessions remain recorded. The standalone spectrum bridge retains its historical default of one window.

On a host without a graphical display, add `--headless`. The owned Nix Chromium browser automatically presses Start and records the same live and completed viewer. It downloads no browser. `--http-port 0` selects a free localhost port before installation; the bound socket passes directly to the viewer process. Interactive Start has a bounded 120-second wait. `--seconds` permits shorter diagnostics, but the acceptance gate requires a successful 60-second physical session.

The Task bindings are `demo:esp` for `python3 tools/demo_esp_sdr.py run`, and `demo:esp:restore` for its `restore` action. CLI help does not inspect or open hardware:

```sh
nix develop --command task demo:esp -- --help
nix develop .#ci --command python3 -m unittest discover -s tests -p test_demo_esp_sdr.py
```

If the firmware artifact needs rebuilding, use `nix develop .#firmware --command task firmware:build` with the pinned source checkout and explicit fresh build/output/evidence paths documented by that task's help. Firmware compilation and artifact hashing establish an installable candidate, not physical reception or byte equivalence with an earlier build.

## Preservation and cleanup

Before installation the tool verifies both private 4 MiB preservation images against the committed preservation SHA-256, confirms the stable symlink resolves to the expected USB VID/PID, and independently reads the current full flash. If the current image differs, it retains that private read and refuses to install or restore over the unexpected image. The operator must resolve that state separately.

After **any installation attempt**, including a partial failed write, unsuccessful capture, Ctrl-C or SIGTERM, the tool stops and waits for its owned browser and capture processes before restoring. Process creation defers ordinary cancellation until child ownership is registered; cleanup checks the whole process group, including an esptool descendant after its Python leader exits. A terminated capture process releases its UART descriptors through the operating system. If an owned hardware group cannot be confirmed absent, competing restoration is blocked and recovery is reported unverified; even an unreaped zombie conservatively blocks that check. Installation/restoration uses the existing guarded flash helper without force or eFuse writes. Restoration independently rereads all 4 MiB and checks the preserved SHA-256, then observes the original `hello_world` / `8b73cb1-dirty` application, ESP-IDF `v5.4-dirty`, and both GPIO toggle messages. A matching readback without the expected boot is reported as incomplete recovery. Ordinary cancellation during restoration is deferred until verification ends.

The command takes longer than the 60-second RF interval: initial and restored full-flash reads each took approximately 100 seconds in earlier preservation work, with flashing and boot observations additional. SIGKILL, host loss or USB removal can prevent automatic cleanup. Keep the private baseline and run explicit recovery with fresh directories after resolving device access:

```sh
nix develop --command task demo:esp:restore -- \
  --output docs/evidence/esp-demo-recovery-next \
  --private .scratch/esp-demo-recovery-next
```

Recovery intentionally does not require the current flash to match the baseline; it restores the previously verified image. It verifies that image and stable USB identity first, checks the full restored readback and expected reset boot, and returns failure if verification is incomplete. A reset boot does not independently prove electrical power removal or reapplication.

## What the evidence means

| Output | Meaning |
| --- | --- |
| `demo.json` | Tool SHA-256, timestamps, source/SDK revisions, exact installed part hashes/sizes/offsets, receiver manifest/build-info hashes and capture/restoration outcome; no stable USB identifier or personal paths |
| `before-install.json` | Actual current full-flash bytes/hash and baseline comparison |
| `spectrum.json`, `spectra.csv` | Accepted prefix frame counts/hash/bytes, requested grouping and returned FFT/sample/end-total checks, timing, nominal sampled coverage and retained failed outcomes |
| `live-spectrum.png`, `completed-spectrum.png` | Actual browser displays during and after the session; screenshots alone do not prove RF reception |
| `restoration.json` | Independent full-flash comparison and boolean observations of the known original application; no raw boot data |
| Private directory | Exact accepted frames and separately rejected consumed frame bytes, full flash reads, subprocess logs, raw reset boot and browser profile, under ignored `.scratch/` or `backups/` with restrictive permissions |

The browser polls an owned localhost HTTP **UART bridge**. It does not use native Web Serial. Frame CRCs, consecutive sequences and matching `SPECEND` totals establish transport integrity. The reader requires the snapshot-gap flag; the demo additionally requires both firmware and host elapsed duration to reach the requested seconds, beyond the existing reader's 95% duration tolerance. Each frame represents separate captured FFT windows with reception gaps; nominal coverage is sampled pairs divided by the advertised sample rate and elapsed host time. This does not independently calibrate the sample clock.

The plot uses firmware power codes 0–255, **uncalibrated, not dBm**. It does not identify signals, network names or devices. It does not prove continuous reception, burst detection rate, sensitivity, dynamic range, or successful BLE decoding. Failure outcomes remain failures even when original-flash recovery succeeds.

Eight-window grouping acquires eight separate snapshots, computes each FFT, averages **linear FFT power** per frequency bin, then converts that mean to the firmware's display code. It changes temporal aggregation and may hide brief changes. Each emitted frame must return exactly the requested FFT count, `bins × FFT count` sample pairs, mean-detector flag, valid CRC and gap flag; end totals must match. The source checks its duration deadline after a complete group, so partial groups are rejected. This reduces per-FFT emission overhead eightfold; actual elapsed frame and byte rates must be measured rather than inferred. Failed runs retain their accepted prefix and consumed rejected-frame hash/length/CRC comparison without treating that prefix as successful completion. The narrow rejected-frame retention covers bytes consumed for a known malformed frame or unknown magic; a short-read exception does not currently preserve its incomplete buffer.

Primary source: [ESPARGOS ESP-SDR at the pinned source revision](https://github.com/ESPARGOS/esp-sdr/tree/550fadea4d00a9e26ce921c5832167becb3dc20c). Preparation and prior physical evidence are in the repository's original-image preservation, UART firmware, and spectrum-baseline receipts. The OpenSpec demo evaluation tracks the physical session, complete recovery proof and independent review. The Nix-built candidate is a separate artifact; a successful compilation does not inherit the historical artifact’s reception result.
