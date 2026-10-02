# Separate receiver-register diagnostic overlay

This is an unverified, read-only stage observation of the forced-selector field
and bit23. It is not a live analog-gain measurement or a reception result.
[Protocol](../../docs/research/receiver-register-observation-protocol.md).

`base/` contains exact source bytes from the GPLv3-licensed
[ESPARGOS ESP-SDR revision 550fade](https://github.com/ESPARGOS/esp-sdr/tree/550fadea4d00a9e26ce921c5832167becb3dc20c):
`main/targets/esp32/receiver.c`, `main/common/rx_bandwidth.h` and
`main/common/rx_tuning.h` and `main/common/burst_serial.{c,h}`. Their hashes
are pinned in `profile.json`.
The upstream license is retained as `base/COPYING`; the overlay and diagnostic
headers are distributed under the same GPLv3 terms.
`overlay.py` deterministically inserts the diagnostic headers and four read
hooks into that receiver. The build copies the pinned project into private
scratch; it never changes the input checkout or SDK.
The diagnostic copy of the common serial parser additionally consults the
armed-session guard before consuming BAUD commands and checks the original
command byte span for embedded NUL before any C-string interpretation. The
actual application loop uses a shared dispatch guard for overlong parser errors.
Armed malformed commands fail the session; after incomplete DATA, all further
command/error output is suppressed. Unarmed behavior stays
unchanged; no general SDR source or artifact approval is altered.

The host-only tests compile that generated receiver's real acquisition, packing,
manual application and command bodies. MMIO, timer, PHY/filter and UART are
controlled shims. These are software tests, not hardware reception or restoration
proof. The builder exports a separate diagnostic manifest, with actual linked
buffer ranges and security/configuration checks. It never opens a device.

Existing SDR artifact approval is intentionally unchanged. Installation requires
its own reviewed diagnostic artifact guard and exclusive preservation/restoration
supervisor. No Bluetooth source is operated by the firmware or builder.
