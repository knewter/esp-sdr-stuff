# Configuration-only 1 Mbaud trial

Evidence class: **Physical flash write and startup captures**, October 1, 2026.

The [locally built UART variant](../firmware-uart1m/README.md) was flashed after full original-image restoration/readback. [Write output](write.log) verifies each part's hash; [manifest](manifest.json) records source and variant.

[Fresh boot inspection](boot-inspection/boot.log) and a [twelve-second console capture](boot-12seconds.log) identify `550fade-uart1m`, SDK `25fe69f9`, single-core 240 MHz operation, and entry into `app_main`. The long capture shows no repeated boot or panic text.

The 1 Mbaud host SYNC attempt still received no acknowledgement. A later probe waited 1.5 seconds after opening and sent INFO, SYNC and BAUD? with no replies. This does not establish an ADC/RF failure: radio initialization precedes transport initialization, and actual physical UART timing remains an uncertainty. A step-marked diagnostic build is being prepared to distinguish these causes. No snapshots or browser spectra are accepted from this trial.
