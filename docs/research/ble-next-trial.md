# Reproduce reception before changing the source limiter

This is a prospective operator protocol and offline readiness record. It closes
no hardware task and changes no acceptance gate. The root operator alone owns
the selected ESP serial port and host Bluetooth controller.

## What the existing evidence distinguishes

The [first 549 snapshots](../evidence/ble-owned-decoding/README.md) contain four
complete CRC-valid exact-marker packets; the [246 controls snapshots](../evidence/ble-controls-decoding/README.md)
contain one. All five protected PDUs are type 0 / ADV_IND. A later
[BlueZ monitor receipt](../evidence/ble-dumpcap-source/hci-control.json) records
properties `0x0013`, all three primary channels (`0x07`), 20 ms interval,
LE1M, exact marker, duration zero and MaxEvents zero. It does not retrospectively
measure the first runs' HCI configuration.

Every failed direct-HCI count/timer trial instead used properties `0x0010`,
channel map `0x01` and **nonzero** MaxEvents. The [ten-episode RF discriminator](../evidence/ble-zero-counter-rf/README.md)
found no valid owned packet. Its null result cannot locate the fault. PDU
properties, channel map and event limiter all differ between the positive and
negative paths; changing them together would not identify a cause.

The [BlueZ advertising API](https://github.com/bluez/bluez/blob/master/doc/org.bluez.LEAdvertisement.rst)
defines requested type and interval, with Release indicating removal. It offers
no emitted-packet counter. The helper now records its executed SHA-256 and
requested schedule, retains connection failures without private error text,
and fails an episode released before its scheduled removal. Existing receipts
remain historical records produced by their original helper revisions.

## Trial A: the known BlueZ reception control

Keep ESP receiver settings pinned to the original four-packet run: LO 2401 MHz,
requested filter 12 MHz, hardware AGC, nominal 16 MS/s, 8-bit I/Q, 16,380 complex
samples and verified 921600-baud receiver firmware. Record identity selection,
firmware hash, setting acknowledgements and fixed physical placement. No antenna
distance, calibrated power or oscillator accuracy is assumed.

Reserve the already identified controller; verify powered state and zero active
BlueZ advertising instances without modifying adapter settings. Start the
sanitized monitor, wait for validated readiness, then start receiver acquisition.
Record at least 20 seconds OFF before the first source registration. Predeclare
three episodes: each 120 seconds registered with 20 seconds OFF between them,
using the existing `broadcast` request, interval 20 ms and exact marker
`0fffffff4553502d5344522d4556414c`. Continue acquisition for **more than ten
seconds after actual final source cleanup and bus closure**. A suggested 460-second
receiver bound provides margin, but the actual receipt must prove the tail;
extend within the capture tool's 600-second limit before the deadline if needed.

The source command, through a Task binding, is:

```sh
nix develop --command task source:ble-bluez -- \
  --output FRESH-SOURCE-DIRECTORY --episodes 3 --seconds 120 \
  --off-seconds 20 --interval-ms 20
```

Replay every saved private waveform with the existing bounded blind decoder,
channel 37, digital translation −1 MHz and refinement. Verify every hash, length,
sample count and transport CRC. A positive demo packet requires protected CRC24,
complete exact owned AD and full nominal preamble-through-CRC window within the
snapshot. Report its actual PDU type, AA/preamble errors and duplicate-hypothesis
collapse. Do not train or repair bits from the marker.

Use the **whole command-send through complete payload-receipt bracket**, with
one-second guards, for source-phase joins. Retain boundary snapshots, failed
registrations, premature releases and zero-hit repetitions. Verify all three
OFF/ON pairs independently. A positive in only one pair is a working demo,
without proving the three-pair RF requirement. A null result remains inconclusive;
do not expand decoder bounds after inspecting this dataset. Record monitor
parameters actually observed, rather than substituting the API request.

Registrations, timestamps and snapshots are not emission counts. The source
denominator remains null and the ≥100 counted-event task stays open even if this
control reproduces owned packets.

## Trial B: remove only the direct-HCI event limiter

Run only after Trial A produces a current positive receiver control. Preserve
direct-HCI handle 1 (externally reserved), properties `0x0010`, channel 37,
interval 20 ms, LE1M, exact AD and five-second duration. Change **only** MaxEvents
from 255 to zero. This setting was not used in earlier direct-HCI trials.

```sh
nix develop --command task source:ble-direct:container -- \
  --handle 1 --interval-ms 20 --events 0 --unlimited-events \
  --duration-ms 5000 --start-delay 0
```

The explicit opt-in requires duration 100–5000 ms in exact 10 ms units. There is
one enable, a bounded duration-plus-five-second host wait, and handle-specific
disable/remove cleanup. No reset, event-mask write, adapter power change,
fallback or automatic restart occurs. Keep a monitor and receiver spanning three
predeclared repetitions with five seconds baseline, one-second OFF gaps and a
continuous tail longer than ten seconds; retain every diagnostic exit code 2.

The source wrapper uses the flake's separate Python image with only NET_ADMIN
and NET_RAW, a read-only filesystem and one read-only bind of the fixed source
helper. It exposes no host USB devices and writes sanitized JSONL to stdout.
SIGINT/SIGTERM request graceful source cleanup before any forced container
removal. Container disappearance proves socket release; successful native
disable/remove and socket-closure receipts separately prove controller cleanup.
Do not start another HCI operation if either cleanup proof remains unverified.

With MaxEvents zero, the termination event's completed-count field is **required to be zero**
under Core 6.2 and cannot be a meaningful source denominator. Store its raw numeric field with
`termination_count_field_meaningful=false`; never accept it as a count, even if
nonzero. The existing status `0x43` / exact nonzero requested-count gate remains
unchanged. A packet associated with the unlimited trial demonstrates that
configuration can radiate a receivable marker; it does not independently prove
what happened in an earlier nonzero-limit trial. If positive, a subsequent
prospectively paired comparison can isolate the limiter further. If null, return
to the retained controls rather than repeating identical failed settings.

## Nix monitor permissions and cleanup

The flake's dumpcap lacks the host-installed binary's ambient file capabilities.
`tools/ble_dumpcap_container_monitor.py` uses the Nix-built monitor image, resolved
to an immutable local image ID. It runs a fixed Bluetooth-monitor command with
host networking, capability `NET_RAW` only, all other capabilities dropped,
no-new-privileges, a read-only filesystem and **no host mounts or USB devices**.
The unprivileged parent immediately sanitizes its stdout pipe and discards stderr;
no raw HCI capture is written to disk.

[libpcap's monitor backend](https://github.com/the-tcpdump-group/libpcap/blob/master/pcap-bt-monitor-linux.c)
binds a Bluetooth MONITOR socket and identifies CAP_NET_RAW as the relevant
permission. It does not inject packets or provide meaningful loss statistics.
The wrapper's random owned container name is removed on every exit, including
parser failure or timeout. Failure to remove it cannot become successful monitor
completion. A terminating Docker client alone does not prove socket release.

```sh
nix develop --command task capture:ble-monitor:container -- \
  --seconds 480 --output FRESH-MONITOR.json
```

Host-only tests check capability/mount policy, immutable-image validation,
exact-name cleanup, parser-failure cleanup, bounded unlimited-mode encoding,
unchanged counted-mode behavior and source release/privacy failures. Actual
container monitor access and reception still require the root operator's physical
receipts. Restore the ESP original image and verify it after the trial.

## Trial C: reproduce the previously verified 10-bit receiver profile

The new [Trial A control](../evidence/ble-bluez-control-001/README.md) completed
1,251 transport-valid captures and three complete source episodes, but its
predeclared full replay found **zero** verified owned packets. The actual HCI
configuration matched the earlier monitored BlueZ proxy: properties `0x0013`,
channel map `0x07`, 20 ms interval, LE1M, exact marker, Duration zero and MaxEvents
zero. This null result does not isolate a source-mode change. Trial B remains
conditional on a current positive control and is not justified by Trial A alone.

The next prospective reproduction control uses the exact receiver cell of the
[previously verified capture 103](../evidence/ble-controls-decoding/README.md):
LO 2401 MHz, nominal 16 MS/s, 16,380 pairs, **10-bit I/Q, requested filter 20 MHz,
manual gain 48**. Relative to Trial A, precision, filter and gain all change. This
is a known positive **profile control**, not a single-variable causal experiment,
and gain 48 is not claimed optimal or calibrated. Keep physical placement fixed,
the same three 120-second BlueZ episodes, 20-second OFF gaps, requested 20 ms
interval, source marker, monitor readiness, baseline and strict >10-second tail.

The capture Task now accepts `--bits 8|10`, defaulting to 8. Every wire request,
payload unpacking, statistic and manifest uses the selected precision; transport
CRC and returned sample count remain independent guards. The private reviewed
runner exposes only two pinned presets, `original-8bit` and `known-10bit`.
The latter sends `--bits 10 --bandwidth 20 --gain 48 --frequency 2401` without
changing the source schedule or controller state. Its future receipt must verify
those settings and actual `OK` acknowledgements, not merely the CLI intent.

The root operator's private, finite launch recipe uses fresh directories:

```sh
nix develop --command task -t .scratch/run_ble_control.task.yml run -- \
  --receiver-profile known-10bit \
  --artifact .scratch/historical-uart921600 \
  --manifest .scratch/historical-uart921600/manifest.json \
  --private .scratch/ble-bluez-control-002
```

The private runner and artifacts must already exist; this is an operator recipe,
not an automatic download. It preserves and validates the current original image
before guarded installation, retains all outcomes privately, confirms owned UART
closure, then verifies full original-flash restoration and its reset boot. Root
review must precede execution. No electrical power-cycle proof is inferred.

Replay all future Trial C waveforms with the **unchanged** bounded blind decoder,
`--rate 16000000 --bits 10 --samples 16380 --channel 37
--frequency-translation-hz -1000000 --refine`. Use whole command-to-payload
brackets and the same one-second guards for phase joins; retain zeros, boundary
snapshots and failures. Do not expand the search or repair bits after examining
the trial. A positive profile may justify later controlled comparisons, while a
null remains inconclusive. Neither outcome supplies an emitted-event denominator
or accepts the counted-source gate.

## Completed controls and next source-reference diagnostic

[Trial C](../evidence/ble-bluez-control-002/README.md) has now completed:
all **997** known-10-bit waveforms pass integrity checks, three source episodes
and guarded phases pass, and the independent complete fixed-bound replay
finds **zero** owned packets. Full original-flash readback and reset boot pass.
Together A/C retain **2,248** valid waveforms with null decodes. This does not
prove that the source did not radiate or that this ESP cannot receive it.
Conditional Trial B remains withheld; neither fresh control supplies its
required SDR-positive condition.

The next planned diagnostic uses a **separate native observer-only BLE app**
on the same preserved ESP. It checks source receivability through the supported
Bluetooth stack at the trial's current placement. This is not hidden-SDR
decoding, an independent hardware reference, simultaneous evidence for A/C,
a channel-37 measurement or a transmitted event counter. Native scanning
hops primary advertising channels. A native null remains inconclusive.

Before execution, independently review its pinned Nix SDK build, exact artifact
parts and observer-only configuration, fresh baseline preflight, bounded
process ownership and full-flash/reset-boot restoration. Keep the SDR artifact
allowlist unchanged. Use finite passive discovery, duplicate filtering off,
no connections, scan requests, advertising, pairing or NVS erase. Discard
foreign AD and addresses before any app output; retain only exact whole
owned-marker receptions, readiness, monotonic timing and bounded aggregate
RSSI/count diagnostics. SDK or UART errors fail the trial, not a reception count.

Predeclare at most 90 seconds native observation, at least ten seconds initial
OFF, three ten-second episodes of the same known BlueZ source with five-second
OFF gaps, then more than ten seconds after actual source cleanup/bus closure.
Start source only after successful native scan readiness and monitor readiness.
The host monitor checks actual settings/ACKs and owned source cleanup; unchanged
unlimited source counts remain null. Keep physical placement as found, with
antennas/distances explicitly unknown unless inspected or supplied. Every
phase uses complete timing brackets and conservative boundary guards. Do not
start another source operation if controller or process cleanup is unverified.

A native positive can guide a later prospectively declared SDR receiver or
placement comparison. It does **not** satisfy the current Trial B SDR-positive
prerequisite, the three-pair SDR RF gate, or the ≥100 counted-event gate. No
new acceptance requirement is claimed by this preparation.

## Retained native failure and version 2 stop contract

[Native trial 001](../evidence/native-ble-source-reference-001/README.md)
delivered 1,160 matching reports but failed completion: the observer-only pinned
SDK omits its GAP timer dispatch with both connection roles disabled. All source
and monitor processes closed, and the full original flash and boot were restored.
This failed prefix does not fulfill the prerequisite for the gain observation.

Version `native-ble-ref-v2` retains the 90,000-ms passive discovery request and
all source/radio settings. The application now deliberately cancels at nominal
ESP elapsed time at least 90 seconds. CONFIG, build profile and END identify
`completion_mode=application_cancel`; END must record actual cancel return zero,
discovery inactive, elapsed 90–92 seconds, and frozen counters. The public cancel
API waits for the controller's scan-disable acknowledgement. It emits no natural
discovery-complete callback. An unexpected completion, early inactive scan,
failed cancel, active scan after cancellation or overrun fails the trial.
No SDK patch or connection role is added, and v1's failure remains unchanged.

The actual v2 artifact and lifecycle passed independent review. [Native trial
002](../evidence/native-ble-source-reference-002/README.md) completed the declared
three-episode schedule with 1,176 matching reports, successful explicit stop at
90.092830 seconds, source cleanup and verified full restoration. The enabled
[gain-state observation](../evidence/gain-state-diagnostic-001/README.md) then
completed twenty integrity-valid fixed snapshots in 10.299817 seconds. All 41
queries reported MANUAL/48 and bit23=1, followed by full original restoration.
There was no queried manual-enable mismatch in this run. Effective gain, earlier
gain state and bit state during each acquisition remain unmeasured.

Native success still does not satisfy Trial B's SDR-positive prerequisite or any
SDR/channel-37/count acceptance gate. No source was controlled during the gain
probe, and no settings were reapplied. The fresh SDR nulls remain unresolved;
any further receiver or placement comparison requires prospectively declared
conditions. Neither this native reference nor the gain queries supply emitted
event counts.

## Direct-source comparison and next receiver observation

The separate [native direct-source comparison](../evidence/native-direct-reference-002/README.md)
now completes all six alternating MaxEvents 255/0 episodes with 363 owned
reports, successful explicit stop, all acknowledged cleanup and full original
restoration. All six have guarded positive native reception, while all six
actual terminations remain `0x3c/count0`. Both source settings are therefore
receivable through the supported observer. Neither the total reports nor the
zero controller fields supply an emitted denominator or causal diagnosis.
The [first failed comparison](../evidence/native-direct-reference-001/README.md)
remains failed with five conditions unrun; it is not repaired by the second run.

A [prospective receiver observation](receiver-register-observation.md) would
read the forced-selector field alongside bit23 at declared acquisition stages,
buffering diagnostics in RAM and reporting after payload delivery. It is
unimplemented and requires a separate reviewed artifact and OpenSpec protocol.
The completed gain query observed bit23 only; no field is equated with effective
analog gain or calibrated dB. Keep the existing SDR allowlist, five historical
positive packets, 2,248 fresh nulls and Trial B prerequisite unchanged.
