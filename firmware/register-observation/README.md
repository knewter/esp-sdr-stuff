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

Each stage additionally reports `hook_cycles`, a raw unsigned 32-bit modular
CCOUNT difference. The wrapper brackets the full non-inlined observation body:
entry/return, eligibility/capacity checks, pointer lookup, both
`esp_timer_get_time` calls, the single RX_GAIN read, original record stores and
record-counter increment. Compiler memory barriers preserve the bracket. The
new field makes each record exactly 32 bytes (81 records, 2,592 bytes); ELF/map
validation rejects the former 24-byte record array. Actual target disassembly
must confirm the bracket before installation.

This measures hook-body elapsed CPU cycles, including any interrupts or task
preemption in that interval. It does not isolate deterministic CPU execution
cost. The fixed profile guards 240 MHz, a single core and disabled dynamic power
management; division by 240 is only a nominal microsecond conversion. No cycle
counter is reset or written. Subtraction handles one ordinary wrap, but an
interval spanning a whole 2^32-cycle period (about 17.9 seconds at 240 MHz) is
ambiguous: do not infer an exact elapsed duration from that raw value alone.
Existing nominal read times and the independent host/session deadlines remain
separate observations, not a proof that such a long pause was impossible.

The two counter-boundary reads, delta calculation, final `hook_cycles` store,
wrapper/callsite entry/return and any code outside the bracket remain residual
measurement overhead. Source review plus the actual target disassembly must
enumerate those instructions; their elapsed cost, memory/interrupt latency and
total RF perturbation are not calibrated or claimed zero. The read-time fields
still delimit only the MMIO/timestamp subinterval. This diagnostic adds no
benchmark loop, heap allocation, UART/disk access or RF write inside acquisition.
Synthetic host cycle costs and wrap fixtures test coverage/arithmetic only,
and provide no hardware performance measurement.
