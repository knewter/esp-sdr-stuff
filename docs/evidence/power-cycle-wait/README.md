# Physical power-cycle gate remains open

Evidence class: **Host observation**, not successful power-cycle recovery.

After the final byte-verified restoration, the serial port was closed and a
600-second observer watched the stable ESP32 USB path for disappearance and
reappearance. [The record](observation.json) reports no disconnect before its
timeout. No user confirmation of physical power removal was received.

This result supplies no cold-boot proof. A reset log labeled POWERON_RESET does
not independently prove cable removal. Both recovery tasks remain open.
Opening UART after reconnection may cause an additional reset; future proof
must preserve that distinction and actual user confirmation.

The board remains on its original GPIO firmware, and all device handles are
closed. See [final restoration](../final-restoration/README.md) for full readback
and reset-boot proof already completed.
