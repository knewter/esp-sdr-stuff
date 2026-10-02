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

## Evaluation status and needed inputs

| Evaluation | Remaining physical requirement | Needed next input |
| --- | --- | --- |
| Recovery | Complete for the preserved baseline and performed trials | User-confirmed cycle plus matching original boot accepted by independent review |
| RF path | Three repeatable controlled pairs, filter/gain/tuning characterization and uncertainty | Known RF source/reference, attenuator inventory and a reproducible physical setup |
| Burst reliability | At least 100 events with a recorded source count, complete hits and unresolved misses/truncations | An observable source counter independent of ESP decoding; requested intervals or event limits are insufficient |
| FPGA feasibility | Actual board/electrical/clock inventory, synthetic sequence/CRC/stall measurements, conditional RF integration | Forgix USB and MCU backup verified; PCB revision, oscillator and header wiring still needed; PCI-card details remain unknown |
| Receiver comparison | Complete: fresh dipole FM/RDS, equipment inventory and independent review | Shared-signal sensitivity explicitly deferred; no conversion/reference equipment reported |

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

The snapshot-transport, recovery and receiver-comparison proposals are accepted and archived. Three evaluations
remain open; checked tasks retain their original requirements. See the
[independent requirement audit](../independent-review/requirement-audit.md) and
[measured recommendations](../../research/measured-recommendations.md).

[USB hub inspection](../usb-power-control/README.md) finds advertised individual
port switching via a scoped descriptor-only container. Electrical VBUS/ESP-rail
removal remains unmeasured; logical port state alone was not recovery proof. The later user-confirmed physical cycle and matching application boot close recovery under its original scope.

[The independent zero-counter review](../ble-zero-counter-independent-review/README.md)
reproduces the complete null replay, all raw integrity checks, source-only timer
receipts and latest full-image restoration. It closes no additional hardware
acceptance gate.

The user confirms actual ESP power cycling. [Fresh matching application boot](../user-power-cycle-recovery/README.md)
and [independent review](../power-cycle-recovery-review/README.md) close recovery.
[Current equipment inventory](../user-equipment-inventory/README.md) supplies a
dipole antenna and reports no external RF equipment. [Fresh dipole reception](../rtl-dipole-rds/README.md)
again decodes WXJC with FEC disabled. Forgix now has [verified USB identity and MCU flash preservation](../forgix-preservation/README.md); its factory application returns after the ROM round trip. PCB revision, oscillator and header wiring remain uninspected, and no FPGA firmware has been replaced.

[Current-dipole independent review](../rtl-dipole-independent-review/README.md)
replays the no-FEC output and accepts the original comparison tasks. No cross-band
sensitivity ranking or all-band antenna performance is accepted.
