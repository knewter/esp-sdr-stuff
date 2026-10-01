# Owned BLE test source registration

Physical controller configuration check, 2026-10-01. A two-second advertisement
registration was accepted over the unprivileged system BlueZ D-Bus API;
unregistration was accepted and active advertising instances returned to zero.
The record in [results.json](results.json) contains no device address or network name.

The source requests a nonconnectable broadcast advertisement containing only a
known manufacturer-data marker, `ESP-SDR-EVAL`, under test ID `0xffff`. No
controller power, discoverability or pairing settings were changed. Primary
channel PHY defaults to LE 1M according to the
[BlueZ advertising API](https://bluez.readthedocs.io/en/latest/advertising-api/).
Legacy advertising RF channels are 37/38/39 at 2402/2426/2480 MHz; actual reception
and packet decoding require separate physical proof.

Registration success proves configuration acceptance, **not** that an RF packet
was observed, its exact interval, or its actual emitted count. The controller
repeats autonomously, so one registered episode can include many packets on
several channels. The strict counted-emission gate remains open until actual
RF ground truth is available. This does not count two seconds as a radio test.

Command: `python3 tools/ble_owned_source.py --output .scratch/ble-source-registration --seconds 2`.
The tool safely unregisters on normal completion, interruption or cleanup.
