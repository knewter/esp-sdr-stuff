# Independent recovery review after the reported power cycle

**Verdict: recoverable for the preserved original image on the evaluated
ESP32-D0WD-V3 board.** The composite evidence satisfies the original recovery
tasks 2.1 and 2.2 and the preservation/restoration requirements. This review
read existing files only; it opened no device and sent no hardware command.

The acceptance criteria require preservation before experimental firmware,
restoration after an SDR trial, a power cycle, a matching application boot,
and a recorded recovery decision. They do not require an electrical rail
measurement or a UART capture synchronized to the first supply edge.

## Evidence and acceptance

| Original criterion | Independently reviewed evidence | Decision |
| --- | --- | --- |
| Full private preservation before experimental firmware | [Preservation manifest](../firmware-preservation/manifest.json) records two matching 4,194,304-byte reads. Both existing private files were rehashed during this review. Prior trial provenance was independently reviewed in [the restoration and RF review](../ble-zero-counter-independent-review/README.md). | Satisfied |
| Task 2.1: after a separately scheduled SDR trial, restore the preserved image and power-cycle; capture a matching application boot | [Post-SDR restoration](../zero-counter-restoration/README.md) records successful full-image write and independent readback, followed by the user's explicit report, “i power cycled the esp”, and [a fresh matching boot](../user-power-cycle-recovery/application.log). | Satisfied by the combined record |
| Task 2.2: review the evidence and record recoverable/not-recoverable with failed steps | This independent review records recoverable for the original image and states the observation limits below. No failed restoration step is identified in the reviewed sequence. | Satisfied |
| Restoration has physical proof: fresh boot and application behavior match the baseline | Baseline, latest reset-restoration boot and post-reported-cycle boot agree on project, version, IDF, ELF hash prefix, CPU frequency and application offset. Both alternating GPIO log states are present. | Satisfied |

The three existing private images checked here—both preservation reads and
the latest restored readback—are each 4,194,304 bytes, mode 0600, SHA-256
`6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`.
The readback precedes the reported power cycle; this review did not initiate
another flash read after the cycle. Root, the sole operator, reports that no
new image was installed between restoration and the new observation.

The new boot identifies `hello_world`, app `8b73cb1-dirty`, ESP-IDF
`v5.4-dirty`, ELF prefix `aa93ad9da67f1e9d...`, CPU 160000000 Hz and app
offset `0x10000`, matching the captured baseline. The retained original
2 MiB image-header warning on physical 4 MiB flash also matches the baseline;
the full private preservation and readback cover all 4 MiB.

## Observation limits and receipt integrity

Physical power removal/reapplication is the user's reported action. The
host directly observes a matching boot after that report. `POWERON_RESET`
appears in the ROM log, but is not an independent measurement of supply
removal. UART opening can cause an additional reset, so neither the log nor
this verdict establishes independently timed first startup at the cold
power edge. The original recovery criteria are met without claiming that
additional measurement.

[Observation metadata](../user-power-cycle-recovery/observation.json) records
stable CP2102 identity confirmation, passive 115200-baud collection, zero
commands, no flash writes or esptool invocation, no intentional RTS/DTR
pulses, and a closed serial handle. These are operator receipts; this
review did not independently witness the physical cycle or serial access.

The receipt distinguishes 5,490 received UART bytes from the 5,028-byte
saved publication log after the documented decoding, ANSI removal and
address redaction. The public and private saved logs are byte-identical,
SHA-256 `82f0e9973c6198882147fbd7579bea5892210290ed2f7b35b1c23cd9916c5ef5`.
Public and private observation JSON are also identical. Recomputed sizes,
hashes and compared boot fields are in [numerical checks](numerical-checks.json).

Earlier receipts correctly leave power-cycle recovery open at their recording
time. This later composite proof supplies the missing reported cycle and
post-cycle boot. The recovery verdict does not close unrelated BLE, FPGA,
or RF evaluation gates, or establish recovery for other images or boards.
