# Owned source for the 10-bit RF-controls trial

Recorded 2026-10-01. The owner registered the same independently chosen
`ESP-SDR-EVAL` manufacturer AD for one bounded 180-second episode with requested
20 ms minimum/maximum interval. [Source results](source-results.json) retain
registration/removal timestamps, intent and cleanup. The registration completed
and the final ActiveInstances value was zero, confirmed separately after exit.
Power, pairing and discoverability properties were not changed; all handles closed.

```sh
python3 tools/ble_owned_source.py --seconds 180 --episodes 1 --interval-ms 20 --output .scratch/ble-gain-trial/source
```

The root operator independently recorded 246 10-bit, nominal 16 MS/s snapshots:
30 source-off baseline windows, 192 filter/gain sweep windows and 24 windows at
requested LO 2402 MHz. Receiver metadata and hashes are in the root's
`docs/evidence/rf-controls-trial/`. This source record alone does not prove RF.

[The retained zero-frame HCI attempt](hci-control.json) used the wrong explicit
channel constant 3 (CONTROL), so it is **invalid monitor evidence**. The correct
MONITOR channel 2 subsequently failed with permission error 1; see
[permission record](../ble-monitor-permission/README.md). Neither interval,
channel map nor event count was observed through HCI during this run. The
requested 20 ms interval must not be treated as an actual-emission counter.

[Offline decoder proof](../ble-controls-decoding/README.md) separately verifies
one complete owned packet from the actual 10-bit samples. The 100-emitted-event
denominator remains unavailable.
