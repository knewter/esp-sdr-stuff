# Independent demo review: failed acquisition, verified restoration

Offline review on 2026-10-02 UTC of [session 001](../esp-demo-session-001/demo.json), executed against workflow checkpoint `576a0771fdc91f79648bd93d694e2da99a1a7224`. The new demo **failed acquisition** with a recorded spectrum CRC error after an accepted prefix lasting about **1.727 seconds**. Its automatic **original-firmware restoration is independently verified**. This session does not satisfy the successful 60-second physical demonstration or completed-display gate. It remains a failed trial even though recovery succeeded.

See [independent numerical checks](session-001-checks.json), [capture result](../esp-demo-session-001/spectrum.json), [retained numerical rows](../esp-demo-session-001/spectra.csv), and [restoration receipt](../esp-demo-session-001/restoration.json). This reviewer opened no USB, serial, Bluetooth, JTAG or other hardware device.

## Retained frame replay and display

Independently parsed the complete private **111,760-byte** retained frame stream: **205 SPC1 spectrum frames and six SPS1 statistics frames**. Its SHA256 is `06c9a98e2614d3a55ff2903ac883dbfa4d73f607513d129c89ea6d8fe89120eb`. Every retained frame passes a separately recomputed CRC. Spectrum sequence is exactly 0–204, sample indices increase, every spectrum carries the gap flag and one 512-pair FFT, and all **205 public CSV rows** match the binary headers, CRCs, gain/power summaries and independently computed means. Public and private CSV files are byte-identical.

Accepted totals are **205 FFTs / 104,960 processed complex pairs**, corresponding to **0.001312 nominal sampled seconds** at the requested 80 MS/s. The last accepted frame arrived at **1.726579764 seconds**. This is gapped snapshot coverage; the nominal rate and sample indices do not independently calibrate the hardware clock. There is no terminal `SPECEND`, no successful host-duration receipt and no firmware-duration proof.

The private reader record reports `ProtocolError: spectrum CRC mismatch`. The rejected corrupt frame itself was not saved, so this review verifies the valid retained prefix and the recorded failure outcome; it does not independently reconstruct the bad CRC bytes or determine the fault's cause. Failed-run frame/hash/timing totals are absent from the original capture JSON because that reader fills those fields on success; the independent checks reconstruct them without rewriting the failed receipt.

Inspected the actual [terminal screenshot](../esp-demo-session-001/completed-spectrum.png): it visibly says **Failed**, reports **205 frames / one CRC failure**, and labels separate snapshots, nominal 80 MS/s and uncalibrated power codes rather than dBm. The filename does not imply a successful capture. No live screenshot was produced because the failure preceded the viewer's five-second screenshot threshold. Screenshot evidence proves the displayed failed session, not signal identification or continuous reception.

## Exact artifact and restoration

Rehashed all three installed files and matched their offsets, sizes and hashes to the actual installation receipt and public demo provenance. Bootloader: 25,792 bytes at `0x1000`, SHA256 `a48cfaef91df68c48dc2a8a7c01b05841abb97b1b8898a38cafb97565b939881`; partition table: 3,072 bytes at `0x8000`, SHA256 `7f00b6c042a89b15b0cac534f82ed988caf29278ff5700b0c511eb1b5bb7c820`; application: 664,608 bytes at `0x10000`, SHA256 `55aae718e026e26783693bcb2be455a8c0453922f3aff5c49e38817bf434c9f6`.

The actual receiver manifest and adjacent build-info hashes match the public installation provenance. Their fields pin receiver source `550fadea4d00a9e26ce921c5832167becb3dc20c`, ESP-IDF source `25fe69f946311abdaf9ad56591f25fedbc20ac98`, target ESP32, no source patch, and only the UART configuration change to 921,600 baud. These are the fresh Nix artifacts; this review claims no byte equivalence with the historical successful receiver build.

Independently reread the recorded **pre-install** and **post-restoration** flash files, each exactly **4,194,304 bytes**, and both original preservation files. All four hash to `6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974` and have mode 0600. The private restored boot contains the original `hello_world` / `8b73cb1-dirty` identity, ESP-IDF `v5.4-dirty`, and both GPIO toggle messages. Those observations agree with every published restoration boolean. The boot is a reset observation, with no new electrical power-cycle claim.

The terminal lifecycle receipt retains `status=failed`, `capture_status=failed`, `restoration_status=verified`, and owned UART worker exit confirmed. Installation and restoration command receipts have exit zero and retain no-force/no-eFuse-write declarations. Static lifecycle review and host tests establish the closure policy; this offline reviewer did not independently watch process exit in real time. Raw flash, boot transcripts, RF frame bytes and browser profiles remain private. The six original public session files are hashed in the numerical checks.

## Lifecycle review and remaining gates

Reviewed executed demo SHA256 `16264e853354f17f0f5f0acc2fa966de0d0df173194644d9cf919955259f3d39` and spectrum bridge SHA256 `b151c0f2610c7dc9559cbca5a5ce7b6f086e7aa9561c20a6a13b6cfe93e0b45b`. Independently ran **32 Nix demo tests**, passing, including real Chromium synthetic display, startup cancellation ownership, restoration's nonraising cancellation handler, strict host/firmware duration failure, full-readback/boot failure gates, and atomic CSV-before-terminal-JSON publication. A separate host-only experiment confirmed cleanup of an exited wrapper's SIGTERM-ignoring descendant before the group-closure check returns.

This proof supports verified recovery after an actual failed installed-receiver session. A successful new **at least 60-second** acquisition with matching frame/end totals, both actual display screenshots, verified recovery and independent replay remains required. The new demo requirements remain unaccepted until those conditions are met. Existing counted-BLE, RF calibration, FPGA transport and deferred AtomVM scope are unchanged.
