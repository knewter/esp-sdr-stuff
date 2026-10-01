# First original-image restoration

Evidence class: **Physical flash write, full readback and reset boot**, October 1, 2026.

Following the first SDR transport trial, the entire preserved 4 MiB image was restored at address zero. [Write output](write.log) reports hash verification. [Independent full readback](readback.log) has the same 4,194,304 bytes and SHA-256 as the original; [manifest](manifest.json) retains this comparison. Raw images remain ignored and private.

[Fresh reset boot](boot-inspection/boot.log) again shows `hello_world`, ESP-IDF v5.4-dirty, CPU 160 MHz and repeated all-pins toggling, matching the [baseline](../preservation-baseline/README.md).

This is successful byte restoration and application reset proof. **Actual USB power removal/reapplication has not been independently recorded**, so preservation task 2.1 and final recovery acceptance remain open. The subsequent 1 Mbaud trial is separately documented and does not replace this historical record.
