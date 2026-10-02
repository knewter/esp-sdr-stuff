# Prospective matched ten-bit gain controls

The fresh manual-gain control was null; earlier eight-bit and ten-bit controls
also differed in precision and bandwidth. These two new controls hold those
settings fixed and change the requested gain mode. This is a supporting
diagnostic under the existing RF evaluation, not a replacement acceptance gate.

## Fixed procedure and inputs

Run MANUAL48 first, then HARDWARE, with a fresh private directory for each.
Each receiver runs 460 seconds, with a 480-second monitor, at least 20 seconds
of initial source OFF, three 120-second source ON episodes separated by at
least 20 seconds OFF, and more than ten seconds of actual payload reception
after the source bus and whole process group have closed. Acquisition totals
920 seconds, plus two complete installation and restoration cycles. Stop the
second run if the first has unknown cleanup or unverified restoration. Retain
failed attempts without automatic retry.

Both controls use the same uninstrumented UART921600 receiver: base
`550fade`, SDK `25fe69`, app SHA-256
`d7a2d80a70134b04e6078d5ac62b728e79ab33364c1845546f7ca321995e4685`.
Recheck every artifact part and build provenance through the existing guard.
No native-reference or register-observation firmware substitution is allowed.
Hold 10-bit components, 16,380 I/Q pairs, nominal 16 MS/s, LO 2401 MHz,
requested bandwidth 20 MHz, and the owned legacy BLE manufacturer AD and
20 ms source request fixed. Preserve physical placement and antenna setup;
introduce no additional owned RF source or heavy replay during acquisition.
Separate restarts, fixed order, calibration and foreign interference remain
confounds. These are three ON/OFF pairs per condition, not three independent
gain crossovers or an analog-gain calibration.

## Ownership and review

The exclusive root hardware operator uses the locked Nix environment and a
private Task caller. A separate copy of the previously checked caller adds
only the ten-bit HARDWARE profile and help text, preserving the original
executed caller. Before hardware, review exact profile arguments and ACK
refusals, readiness, cancellation, source schedule, actual tail, whole-group
closure and restoration cases. Freeze caller, Task, helpers, lock and artifact
hashes. Fresh ignored directories use permissions 0700/0600.

Stable USB identity, exclusive lock, two intact original 4 MiB images and
current original-flash matching precede installation. Whole UART group closure
precedes full restoration, full readback comparison and expected reset boot.
Keep monitor container removal and source unregister/bus disconnect separate
from process-group closure. Unknown UART ownership blocks a competing restore.

## Analysis and decision

Independently verify each source's wire properties `0x0013`, channel map 7,
LE 1M, identical complete AD, requested 20 ms, Duration 0 and MaxEvents 0,
plus accepted cleanup. Monitor lifecycle alone does not prove these fields.
The source remains uncounted; native reports are not an emitted denominator.
The pre-settings gain query and exact ACKs prove requested software mode,
not live AGC index, effective analog gain or calibrated dB.

Decode every new capture with the unchanged channel-37 decoder, 16 MS/s,
ten-bit packing, 16,380 pairs, translation -1 MHz and existing blind search
bounds. Use complete command-to-payload brackets with one-second source-phase
guards. A verified owned packet needs protected CRC24, complete expected AD,
full nominal preamble-through-CRC window, PDU hash/type/error/deduplication and
independent waveform/phase review. Preserve zero and excluded results.

A reviewed path/count adapter may reuse the existing scalar audit's centered
AC, endpoint fraction, integrated Hann +1.5 to +2.5 MHz band, block-32 and
guarded ten-second edges. Freeze the method before inspecting new outcomes;
never overwrite historical results or tune bounds to obtain a positive.

Three repeatable owned source responses remain required for the original RF
claim. One packet is partial evidence; two null controls remain inconclusive.
Code power and rails do not establish SNR or absence of RF. No detection rate
without valid emitted counts, no Trial B release without its original fresh
hidden-SDR prerequisite, and no task completion from this protocol alone.
