# Longer primary capture opportunity: reviewed plan

October 4, 2026. The [prospective protocol](../../research/ble-primary-timed-zero-data-v2-protocol.md) passes independent architecture review and root review. This checkpoint proves the plan only. The source implementation and a new private qualification caller are being prepared; no new source or receiver trial has run.

The [completed fixed receiver trial](../ble-primary-zero-data-receiver-001-review/README.md) preserved 365 snapshots, but only 11 whole windows lay inside guarded source-on intervals. Its zero-packet result remains inconclusive. The new diagnostic requests three 25-second source episodes with the same receiver settings, placement and decoder. Its coverage gate is at least 100 guarded source-on windows in total and 25 in each repetition. These are acquisition windows, not emissions.

Each source episode has a 45-second inclusive cap beginning before its preflight and ending after normal closure and durable verification. The full schedule budgets 159.1 seconds inside one continuous 180-second capture. The timer profile must first pass its own source-only qualification: exact native and monitor fields, five ordered successful acknowledgements, one observed timer termination, matching count metadata, bounded elapsed time and scoped cleanup. A completed-count byte supplies no air denominator.

The old source profile, container image, monitor, decoder and frozen private callers remain unchanged. The new source-bearing Nix package and explicit Task entries will require fresh production source snapshots. Any later register trial must also rebuild its strict source-bound ARM artifact after those flake/Task changes; its existing guard remains intact.

[Sanitized review and dependency record](checks.json) binds the committed plan and private author/peer/root receipts. The official [Bluetooth Core HCI specification](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html), sections 7.8.56 and 7.7.65.18, is the primary reference for the duration and termination fields. Original emission-count requirements, three repeated RF responses and Trial B remain open.

The 18:51 UTC read-only USB survey finds the ESP32 and RTL-SDR, with verified ESP32 backup hashes, but no matching Forgix or RP boot-ROM device. No serial port was opened. FPGA clock, voltage, pin timing, grade and loading still need physical qualification; this diagnostic requires no wiring between boards.
