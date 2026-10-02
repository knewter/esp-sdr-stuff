# Equipment inventory supplied by the user

The user reports no separate RF equipment, a **dipole** currently attached to
the RTL-SDR, and Forgix attached. [The inventory](inventory.json) records those
statements separately from host observations. Antenna model, arm lengths and
orientation remain unknown; no assumption about previous captures is made.

No external signal generator, calibrated reference, attenuator or frequency
converter is reported. The host Intel Bluetooth controller remains an owned
2.4 GHz candidate source, with documented configuration and substantial limits:
its required event-count gate did not pass, timer trials reported zero completed
events, and the RF discriminator was inconclusive. It supplies no calibrated
signal level or reliable emitted-event denominator.

A same-signal ESP32/V4 sensitivity comparison is **deferred** because no
conversion/reference path is inventoried. The new receive-only dipole trial
addresses the separate V4 application gate. Missing RF equipment does not
justify a fabricated sensitivity ranking or rejection of untested tuning points.

Future ESP RF experiments retain the previous nominal LO2401/BW20/gain48/16MS/s
8-bit 16380-sample baseline but require a suitable repeatable source/reference
and a recorded physical setup before acquisition. Filter shape, frequency and
level uncertainty, clipping and event-count reliability remain unverified.

Forgix connection is a user statement. The initial descriptor survey did not
identify a new RP235x or Forgix USB interface. Custom firmware, an unenumerated
MCU or a power-only cable remain possible; no cause is established and no
unknown serial port was opened. Physical revision, clock and wiring still need
identification before FPGA programming.

Later [Forgix identification and MCU preservation](../forgix-preservation/README.md)
resolve the initial USB uncertainty. Earlier descriptor receipts and inventory
remain historical; physical FPGA revision, clock and header wiring are still open.
