# Observe gain state without reapplying it

This is a prospective diagnostic, not completed RF evidence. Execute only after
the bounded native reference finishes with matching owned reports and verified
full-flash restoration. A native positive does not satisfy the separate SDR
positive prerequisite for Trial B in [the source protocol](ble-next-trial.md).

The [pinned ESP receiver source](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c)
returns `GAIN <mode> <software index> 0 <startup maximum> <register bit23>`.
Mode and index are software variables; the last field reads the current
manual-control register bit. It does not read the live gain-index bits or give
calibrated gain. Manual 48 with bit23=1 therefore does not prove effective gain
48. The A/C controls queried gain at startup, before applying their settings;
they provide no per-capture manual-mode observation.

Keep placement as found. Preserve the original image, verify the current full
baseline, and install only the reviewed receiver artifact. The worker applies
LO 2401 MHz, requested filter 20 MHz and manual gain 48 once. Read `GAIN?`
immediately afterward, then perform exactly **20** fixed `CAP20 16380 6`
snapshots, with `GAIN?` immediately before and after each. This means 10-bit
components, nominal 16 MS/s and 40,950 payload bytes per snapshot. Retain every
command's complete send/receipt bracket, returned count, CRC32, saved hash and
byte length. No reapplication, frequency change, filter change, retry or serial
resynchronization is permitted within the loop.

The entire worker acquisition, including initial settings and queries, has an
absolute **30-second** ceiling. This is a bounded register-state observation;
it does not operate the source or require packets. Preserve partial/error
outcomes, close the complete UART worker group, then restore and verify every
original flash byte and the original reset boot. No electrical power-cycle
claim follows from a reset.

A software MANUAL/48 response with bit23=0 would show a mode mismatch at that
query, without establishing its cause or proving it existed in earlier trials.
All queried bits equal to 1 would weaken a persistent mismatch explanation,
without observing the bit continuously or proving effective gain, sensitivity
or calibrated power. Neither outcome establishes RF repeatability, decoder
reliability or an emitted-event denominator. Any later reapplication comparison
needs a separate prospective protocol; it is not an automatic fallback here.
