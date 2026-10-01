# Clean 921600 transport trial, 2026-10-01

**Physical result:** `550fade-uart921600` boots on the identified ESP32-D0WD-V3
and answers the protocol correctly at matching 921,600 host baud. Capture
integrity is evaluated separately in [snapshot baseline](../snapshot-baseline/README.md).

[Build receipts](../firmware-uart921600/README.md) pin source, SDK, configuration
and every artifact hash. The source is unchanged; its UART default and version
label differ from upstream. [Installation manifest](manifest.json) and
[write log](write.log) record exact offsets and esptool verification after the
private whole-flash backup check. [Reset boot](boot-inspection/boot.log)
identifies this application and SDK.

The first manual SYNC attempt after a 1.5-second delay failed. A subsequent
probe waited 2 seconds, drained startup text, then obtained INFO, SYNC and BAUD?
at 921,600; other tested host rates had no replies. See [probe record](uart-probes.json).
The [complete query record](protocol.json) retains INFO, CAPS, LIMITS?, RANGE?,
TRANSPORT?, SPECINFO?, GAIN? and BAUD?. Opening the port can reset the board;
the host handshake must allow for startup rather than assuming readiness.

The reported RANGE 100–6000 MHz describes accepted command parameters.
It does not prove PLL lock, antenna response or usable reception across that
range. Advertised sample rates likewise remain nominal, uncalibrated rates.
