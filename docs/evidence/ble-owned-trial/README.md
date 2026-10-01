# Three owned advertising episodes

Recorded on 2026-10-01. This is physical host-controller configuration evidence
and source scheduling intent, not an independently counted RF emission record.

The source registered three 40-second manufacturer test advertisements with
20-second gaps. The requested minimum/maximum interval was 20 ms. The marker
was independently chosen as `ESP-SDR-EVAL`, AD structure
`0fffffff4553502d5344522d4556414c`. No power, discoverability, pairing, address
or local-name properties were changed.

```sh
python3 tools/ble_hci_monitor.py --seconds 190 --output .scratch/ble-owned-trial/hci-control.json
python3 tools/ble_owned_source.py --seconds 40 --episodes 3 --off-seconds 20 --interval-ms 20 --output .scratch/ble-owned-trial/source
```

Source tool revision: `1674990` (tested lifecycle regression at `af7f7d3`).
Monitor revision: `5755e78`. The commands ran from the agent's isolated worktree.
Source registration acceptance and removal times use the same host monotonic
clock as the independently operated ESP32 capture process.

| Episode | Registration accepted, monotonic ns | Removal accepted, monotonic ns | Active registrations after removal |
| --- | ---: | ---: | ---: |
| 0 | 701498688255271 | 701538721028880 | 0 |
| 1 | 701558855269980 | 701598871414225 | 0 |
| 2 | 701619051166600 | 701659122389056 | 0 |

[Source results](source-results.json) retain all exact timestamps, requested
interval and any observed BlueZ Release callbacks. Every episode removed its
registration; after completion a separate read-only `busctl` check returned
`ActiveInstances = 0`. All source and monitor handles are closed.

[Monitor record](hci-control.json) retains a **zero-frame invalid attempt**.
The script used HCI channel 3 (CONTROL), not channel 2 (MONITOR). A successful
CONTROL bind did not establish monitor access. The subsequently corrected
MONITOR2 bind is denied to this unprivileged operator; see
[permission evidence](../ble-monitor-permission/README.md). These attempts cannot verify
the accepted interval, channel map, advertising data or completed event count.
The 20 ms interval remains a configuration request. No actual emission count
can be inferred from registration success, episode duration or `ActiveInstances`.
The 100-counted-emission proposal gate remains open.

BlueZ's query of the optional missing `TxPower` property produced a D-Bus
UnknownProperty diagnostic; each registration nevertheless returned success.
No transmit-power property was set. This diagnostic is retained as a limitation
rather than treated as proof of either RF success or failure.

The root operator independently captured ESP32 IQ with requested LO 2401 MHz,
16 MS/s, 8-bit components and nominal bandwidth 12 MHz. The chosen source's
primary advertising channel 37 is 2402 MHz. Receiver proof, actual spectral
offsets, CRC decoding and paired on/off statistics are reported separately; raw
IQ stays in ignored private storage because it can encode device addresses.

Protocol/API references and host-only decoder proof are in
[BLE research](../../research/ble-evaluation.md). None of these source records
complete the RF or burst proposal's physical acceptance criteria by themselves.
