# Prospective conditional zero-data primary receiver trial

Declared October 4, 2026 before receiver implementation or hardware actions.
This separately versioned condition follows the [primary profile](ble-extended-primary-zero-data-protocol.md)
and [source-only readiness](ble-primary-zero-data-readiness-protocol.md).
Its prerequisite is the independently reviewed saved source-only trial001,
including exact native/monitor receipts, selected power and normal closure.
A source-profile success is not independent air-count proof. Earlier nulls,
failures, original eight-bit/BW12/hardware Trial B and all original RF/count
acceptance criteria remain unchanged. No physical task is checked by preparation.

## Fixed condition and preservation

Use the exact demonstrated UART921600 artifact, manifest and build-info hashes
already bound by the reviewed radio caller; no new receiver build is necessary
if those immutable bytes and current requested-setting ACKs match. Original
ESP32 stable CP2102 identity, inherited exclusive global operator lock, two
preserved complete 4 MiB reads, fresh pre-install full readback, guarded install,
verified installed application and full original restore/readback/reset boot are
mandatory. Root alone operates both source and receiver. No other serial owner,
controller power/discovery/reset/pairing/mask mutation or interboard wiring.

Receiver: ten signed bits/component, 16 MS/s nominal, 16380 pairs, LO2401 MHz,
BW20 MHz, manual gain48. Actual setting replies must be exactly OK for FREQ2401,
BANDWIDTH20 and GAIN MANUAL48. ADC windows are nominally1.02375 ms; timestamp
brackets cover host request through full UART payload, not calibrated RF time.
Capture180 seconds continuously, preserving every complete row and all private
failure prefixes; never resynchronize/retry an ambiguous consumed command.

Exactly three separately logged source instances use the qualified zero-data
profile: handle1/properties0/map37-only/LE1M/20ms, MaxEvents100/Duration5000ms,
start-delay0, empty complete data and both explicit diagnostic flags. All five
native/monitor command-ACK pairs and actual selected power must agree per
instance. One actual0x43/count100 termination and successful scoped cleanup are
required; timer0x3c, fallback, restart or missing records fail that repetition.
Preserve all three attempts, including nulls/failures; abort further hardware
source attempts on failure, preserving the unexecuted intent explicitly.

Monitor ready before receiver; capture240 seconds, producer readiness15 seconds,
grace5 seconds, active bound260 seconds. Outer launch-through-ready bound75
seconds is anchored before spawn. Receiver startup30 seconds, baseline hold10
seconds (actual >=5 seconds), then three source instances each capped40 seconds,
with2-second OFF holds after natural whole-group closure (actual >=1 second).
The final source must close by receiver-ready+165 seconds; keep receiver and
monitor alive for at least10.1 seconds after that closure, then require the
actual last complete payload >10 seconds after closure. No disjoint tail segment
repairs a failed original schedule. Receiver natural completion cap ready+195
seconds; monitor natural completion cap ready+275 seconds. Acquisition-phase
supervisor420 seconds begins before monitor spawn, after install. Preservation,
install/restore commands retain their existing separately bounded600-second
owned execution and closure policy; cleanup never makes forced completion pass.
All phase checks include spawn, durable intent, lock recheck and post-operation
clock/liveness checks. Repeated cancellation is deferred during owned cleanup
and restoration; unknown UART group ownership blocks restoration.

## Freeze and attribution

Before any action, freeze exact coordinator/private support/test/Task/protocol
bytes, full transitive project helper imports, decoder/parser and unchanged
legacy source/bounds, receiver artifact/build-info, preservation/security inputs
and backups, private stable controller/address references, qualification receipt,
Nix Git/executable/archive/image identities and recursive runtime closures.
No mutable image fallback; read-only image inspection must match frozen IDs.
Current read-only controller binding/powered+idle state is required before source
spawn and unchanged after all closure. Privately owned AdvA reference must match
that binding before capture, never inferred from decoder outcomes.

Offline replay every complete saved waveform at translation-1 MHz with unchanged
public-AA-only search: coarse period4/correlation>0.78/errors<=2 and refinement
13 periods3.97..4.03 x17 offsets+-2 x37 biases-0.45..0.45. Freeze decoder and
search before source labels/outcomes; no outcome-assisted tuning or payload
repairs. Verify each raw SHA/CRC/count and acquisition bracket first.
Full nominal preamble-through-CRC, valid extended type7/profile and exact present
private public AdvA (SID0 if ADI exists) are required. AUX AD and ADI-only ownership
are rejected. AUX omission, actual layout/PHY/AdvA presence are observed, never
assumed. Source-associated positives require the entire acquisition bracket
inside accepted enable+100 ms through termination-100 ms, with agreeing source
and monitor receipts. Distinct owned clusters in one snapshot are unresolved in
all phases, not multiple event hits. Preserve OFF/boundary/foreign/null outcomes.

Per-source controller completed count100 has units of extended advertising
events, not independently counted primary emissions. The aggregate300 does not
close the original deliberately emitted-event gate or establish sensitivity,
misses or reception rate. N-full owned captures means unverified complete
reception, with omissions/gaps/truncation/decoder uncertainty unresolved. A null
is inconclusive. Three scheduled pairs alone do not prove three reciprocal RF
responses. Any public positive requires independent whole-waveform/source join
review, and varying header fields are not independently known whole payload.

Proof before physical admission: locked Nix/Task host fixtures using saved
native/monitor/frame receipts and owned harmless process groups, exhaustive
profile/refusal/deadline/closure/retention tests, exact frozen input/runtime proof
and independent preflight review. No device, compiler or container producer is
run in preparation. Actual source-only qualification remains prerequisite.
