# Evaluation checkpoint — October 2, 2026 UTC

The ESP32 supports the pinned original-chip ESPARGOS receiver. Its clean
921,600-baud build delivers snapshots and has decoded owned BLE data. The
RTL-SDR V4 independently demonstrates FM station-data reception. AtomVM is
explicitly deferred by the user.

## Verified outcomes

- [600 physical snapshots](../snapshot-baseline/README.md) pass CRC and counts;
  nominal listening windows are 0.205–1.024 ms, followed by approximately
  361–451 ms full-payload delivery cycles.
- [A browser spectrum session](../spectrum-baseline/README.md) completes
  60.005 seconds and 7,205 validated 512-bin frames. The failed first
  1,024-bin session remains documented separately.
- [Four 8-bit BLE packets](../ble-owned-decoding/README.md) and
  [one 10-bit BLE packet](../ble-controls-decoding/README.md) carry the exact
  independently chosen advertising marker and valid protected-PDU CRC.
- [No-FEC RDS decoding](../rtl-rds-trial/README.md) identifies WXJC at 101.1 MHz
  in retained and fresh V4 captures; [independent replay](../rtl-rds-independent-review/README.md)
  reproduces both trials.
- [Latest restoration](../zero-counter-restoration/README.md) matches all 4,194,304
  original flash bytes and boots the original GPIO application after reset.
  The board is currently restored; no receiver holds a device handle.

## Open gates and needed inputs

| Evaluation | Remaining physical requirement | Needed next input |
| --- | --- | --- |
| Recovery | Actual power removal/reapplication and recorded original boot | User-confirmed ESP USB unplug/reconnect; current wait timed out without a disconnect |
| RF path | Three repeatable controlled pairs, filter/gain/tuning characterization and uncertainty | Known RF source/reference, attenuator inventory and a reproducible physical setup |
| Burst reliability | At least 100 events with a recorded source count, complete hits and unresolved misses/truncations | An observable source counter independent of ESP decoding; requested intervals or event limits are insufficient |
| FPGA feasibility | Actual board/electrical/clock inventory, synthetic sequence/CRC/stall measurements, conditional RF integration | Connect Forgix and identify revision/wiring; identify PCI-card markings and programming interface |
| Receiver comparison | Inspect RTL antenna; inventory same-signal conversion/reference hardware | Antenna identity/attachment and available converter/reference equipment |

The native corrected HCI MONITOR bind was denied. A capability-enabled
[dumpcap fallback](../ble-dumpcap-source/README.md) now physically records actual
accepted source settings. This unlimited-source trial supplies no event count.
Three [finite source-only diagnostics](../ble-counted-source-smoke/README.md)
also receive successful command acknowledgements but no termination count.
Subsequent [timer diagnostics](../ble-duration-source-diagnostics/README.md)
observe duration-expiry events with an actual completed count of zero. A
[ten-episode RF discriminator](../ble-zero-counter-rf/README.md) retains 262
CRC/count-valid ESP snapshots and finds no CRC-valid owned packet. This null
is inconclusive; no source count or hit rate is established. Its initial short
tail and discontinuous supplemental segment remain explicit.
The [predeclared reporting protocol](../../research/ble-counted-trials.md) is
software readiness, not a physical receiver result.
Historical wrong-channel attempts provide no emission count. No calibration,
event hit rate, continuous ESP IQ or FPGA transport success is inferred.

Only the snapshot-transport proposal is accepted and archived. Five evaluations
remain open; checked tasks retain their original requirements. See the
[independent requirement audit](../independent-review/requirement-audit.md) and
[measured recommendations](../../research/measured-recommendations.md).

[USB hub inspection](../usb-power-control/README.md) finds advertised individual
port switching via a scoped descriptor-only container. Electrical VBUS/ESP-rail
removal remains unmeasured; logical port state cannot close recovery proof.

[The independent zero-counter review](../ble-zero-counter-independent-review/README.md)
reproduces the complete null replay, all raw integrity checks, source-only timer
receipts and latest full-image restoration. It closes no additional hardware
acceptance gate.
