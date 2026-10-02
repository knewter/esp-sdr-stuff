# Original firmware restored after the RF trials

Physical restoration, 2026-10-01. The final SDR capture series closed its UART
handle before restoration. `tools/flash_trial.py restore` wrote the entire
preserved 4,194,304-byte image at offset zero without header overrides, force
or eFuse operations. [Write log](write.log) records esptool verification.

A fresh independent full [readback](readback.log) is exactly 4,194,304 bytes,
SHA-256 `6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`,
matching the original two preservation reads. [Manifest](manifest.json)
records the full image hash and matching result. The private image remains
ignored under `backups/final-restored-readback.bin`, mode 0600.

[Fresh reset boot](boot-inspection/boot.log) again identifies the original
hello_world GPIO application, ESP-IDF v5.4-dirty, CPU 160 MHz and pin toggles.
This establishes the restored bytes and application boot after software reset.
Every serial handle is closed. This checkpoint restored that original application. The [latest restoration
after subsequent diagnostics](../zero-counter-restoration/README.md) verifies
its complete image and fresh reset boot again; it is the current firmware record.

**Physical power-cycle recovery remains open.** The user has been asked to
remove/reapply the ESP32 USB power. The bounded host observer subsequently
timed out without a disconnect; its [record](../power-cycle-wait/README.md)
supplies no cold-boot proof. No serial handle remains open. USB disappearance alone will not be called power-removal
proof; user confirmation and a matching post-cycle application boot are
required. The completed capture/display proposal is independent of this final
recovery gate.
