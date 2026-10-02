# Original application after a user-confirmed power cycle

The user explicitly reported: “i power cycled the esp”. Power removal and
reapplication are operator-reported physical actions. Root then confirmed the
stable CP2102 identity (`10c4:ea60`) and exclusive port ownership and collected
[the application log](application.log) at 115200 baud, with no commands,
flash writes, esptool query or intentional RTS/DTR pulse. The serial handle
closed afterward. [Observation metadata](observation.json) records the actions
and limitations.

The fresh log identifies `hello_world`, ESP-IDF v5.4-dirty, CPU 160000000 Hz,
and alternating `all pins -> 0` / `all pins -> 1`, matching the preserved
baseline application. Its ROM reports `POWERON_RESET`, but that code alone
is not electrical power-removal proof. UART opening may cause an additional
reset even with inactive modem lines. This log therefore proves matching
application boot after the reported cycle, not independently timed first
startup at the physical supply edge.

[Original preservation](../firmware-preservation/README.md) contains two matching
full 4 MiB reads. [Latest post-SDR restoration](../zero-counter-restoration/README.md)
wrote and independently read back all 4,194,304 original bytes, SHA-256
`6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`.
No further image was installed before this observation. Full flash remains
private and excluded from Git and the site.

The recovery sequence combines user-reported physical power cycling with
host-observed matching application boot and independently verified restored
bytes. Electrical rail measurement and exact cold-edge timing were not part
of the original recovery acceptance criteria and are not claimed here.

A later read-only [kernel USB excerpt](kernel-usb.json) records this CP2102
interface disconnect at 03:09:33.970735 UTC and re-enumeration as `10c4:ea60`
at 03:09:41.713475 UTC, before the 03:11:06 application check. This supplies
retrospective interface chronology; it is not an electrical rail measurement.

[Independent recovery review](../power-cycle-recovery-review/README.md) accepts
the original preservation and recovery criteria from the composite evidence.
The reviewed decision is **recoverable** for this preserved baseline and the
performed SDR trials; it is not a guarantee for arbitrary future images.
