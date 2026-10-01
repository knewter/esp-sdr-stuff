# Actual HCI monitor access is denied

Recorded 2026-10-01. The correct Linux HCI monitor channel is **2**; CONTROL is
3. Primary reference: [Linux hci_sock.h](https://github.com/torvalds/linux/blob/master/include/net/bluetooth/hci_sock.h).
The earlier script first used a Python address tuple that selected RAW, then
used an explicit but incorrect CONTROL3 constant. Those retained zero-frame
attempts provide no monitor evidence and no inference about emissions.

The corrected explicit MONITOR2 bind failed with **PermissionError, errno 1**.
[Failure record](hci-control.json) records the real channel and denied-bind
status. No HCI settings or events were received. `sudo -n true` reported that a
password is required; no password or privilege change was attempted.

```sh
python3 tools/ble_hci_monitor.py --seconds 5 --output .scratch/ble-monitor-verified/hci-control.json
```

A separately authorized bounded five-second owned registration/removal
[completed](source-results.json). It was intended to verify actual settings
with the monitor, but permission denial prevented that observation. This probe
has no ESP32 capture and proves only API acceptance and cleanup. A final
read-only ActiveInstances query returned zero. All handles are closed and the
source is off.

Actual interval/channel-map/controller event counts require access to the real
read-only monitor, or another independently counted source. The three-episode
and 180-second source records retain requested settings as requests. Their
decoded owned packets independently prove specific RF receptions, while the
100-event denominator remains open.
