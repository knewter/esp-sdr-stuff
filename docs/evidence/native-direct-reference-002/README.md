# Both direct-source limit settings are received by the native observer

Physical run 002 completed on 2026-10-02. The unchanged native v2 observer
delivered **363 exact owned reports**, acknowledged cancellation and reported
inactive discovery at **90.092890 seconds**. All six predeclared source episodes
completed; their groups closed by READY +70.572797 seconds, leaving an actual
19.538806-second final tail. Full original 4 MiB readback and reset boot verified.
This is native Bluetooth reception, not hidden-SDR decoding or emitted counts.

The [prospective protocol](../../research/native-direct-source-comparison.md)
alternates MaxEvents 255 and 0 three times. Handle 1, legacy nonconnectable
properties, channel 37, LE1M, requested 20 ms interval, five-second duration,
owned 16-byte AD and placement remain fixed. The frozen v3 supervisor preloads
the exact Nix archive before native startup; every source verifies and uses the
same immutable image. Source-only Task `--exit-code` preserves actual diagnostic
exit 2. No automatic retry, fallback or shortened condition occurred.

Every source terminated with **0x3c/count0**. For MaxEvents 0 that count field
is unmeaningful by specification; for MaxEvents 255 it remains inconsistent
with using the controller field as an emitted denominator. All six have
positive guarded native observations. This demonstrates receivability of the
owned marker under both settings, without establishing an Intel firmware cause,
equivalent emission behavior, independently replayed protected PDUs or a rate.

| Episode | Requested MaxEvents | Guarded ON buckets | Owned reports in those buckets |
| --- | ---: | ---: | ---: |
| 0 | 255 | 2 | 24 |
| 1 | 0 | 2 | 23 |
| 2 | 255 | 2 | 21 |
| 3 | 0 | 1 | 12 |
| 4 | 255 | 2 | 24 |
| 5 | 0 | 2 | 20 |

All 90 delivered buckets remain in the [CSV](native-buckets.csv) and
[actual plot](native-reports.svg). Whole firmware intervals and complete READY
receipt brackets are mapped nominally to source ACK/termination and group
closure times, with one-second guards at transitions. The 11 guarded ON
buckets contain 124 reports; 36 guarded OFF buckets contain zero; 43 excluded
transition buckets retain 239 reports. The unequal number of included buckets
precludes comparing their totals as a detection rate. ESP clock rate and
UART/HCI/controller latency are uncalibrated, and reports can duplicate.

## Integrity and recovery

The [native capture](capture.json) records all **23,457** received UART bytes
saved after UART closure, SHA-256
`76ba2496af4043901cd11e6d7f7cd8d125c3fcbcae324674f28d35d0107c8c7b`.
Typed configuration, fresh nonce, contiguous cumulative aggregates and END
validate this JSON stream; it carries no independent transport CRC or protected
BLE-PDU replay. Raw UART, flash and original boot content remain private.

[Source receipts](sources.json) and the separate sanitized
[monitor](monitor.json) agree on 30 commands, 30 successful ACKs and six
terminations. Each own-handle disable/remove succeeds; sockets, containers and
owned process groups close naturally. The wrapper records
`source_controller_cleanup_verified_by_wrapper=false` because it does not
assess HCI cleanup; its separate container-removal proof is true. The supervisor
validates the complete typed controller-cleanup receipts before the next episode.
[Orchestration](orchestration.json) retains these distinctions, the exact
preload proof, actual source return codes and immutable executed-file hashes.

[Restoration](restoration.json) verifies all 4,194,304 bytes against the original
SHA-256 `6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`
and the original application's reset boot. Controller before/after state
matches, all child groups close and no cleanup failure is recorded. This proves
reset-boot restoration, not electrical power removal.

## Reproduce reporting and retain the failure

The sole operator used locked Nix and the private Task command documented in
the protocol, with fresh `native-direct-reference-002` paths. Saved-data
reporting ran through locked Nix CI and
`.scratch/report_native_direct_reference.task.yml`; its SHA-256 is retained in
the [summary](summary.json). It validates the completed supervisor, all six
typed sources, monitor, native aggregates and raw saved length/hash before
exporting the CSV and plot. It opens no hardware.

The [failed first comparison](../native-direct-reference-001/README.md) remains
failed with five unrun conditions and its original frozen caller. Its 59 native
reports and verified recovery remain separate evidence. Run 002 does not
retroactively repair it. The existing 2,248 fresh hidden-SDR nulls, five valid
historical SDR packets, RF repeatability gates and conditional Trial B remain
unchanged. [Independent review](../native-direct-source-independent-review/README.md)
distinguishes preflight from the physical result.
