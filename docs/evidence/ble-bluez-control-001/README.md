# The current BlueZ control has no verified owned packet

Recorded 2026-10-02. Trial A completed **1,251 CRC- and count-valid private
snapshots**, three full owned-source episodes, the monitored cleanup, and verified
original-flash restoration. The predeclared complete decoder replay found **zero
verified owned packets and zero CRC-valid foreign packets**. This is a retained
null reception control. Transport success and accepted source configuration do
not prove an RF emission, missed-packet rate or inability to receive.

The receiver requested LO **2401 MHz**, nominal **16 MS/s**, **16,380 I/Q pairs**,
**8-bit** components, filter **12 MHz**, hardware AGC and UART **921600 baud**.
Actual setting acknowledgements are retained in [receiver.json](receiver.json).
All 1,251 files contain 32,760 bytes: total **40,982,760 bytes**. Every saved file
was independently checked against the capture CSV's SHA-256, expected and actual
CRC32, returned count and full command/header/payload timestamp bracket.
[Input verification](input-verification.json) and the exact [capture CSV](captures.csv)
retain that check's aggregate and input hashes. Raw waveforms remain private.

## Actual source configuration and schedule

The sanitized [HCI monitor](monitor.json) observed each of the three source
configurations, their accepted enable, disable and removal commands, and all
**15 matching successful command completions**:

| Observed HCI field | All three episodes |
| --- | --- |
| Advertising handle | 1 |
| Event properties | `0x0013` |
| Primary channel map | `0x07` |
| Requested minimum/maximum interval | 20 ms / 20 ms |
| Primary/secondary PHY fields | 1 / 1; legacy LE1M profile |
| Manufacturer AD | Exact owned 16-byte marker |
| Duration / MaxEvents | 0 / 0 |

This matches the [earlier monitored BlueZ proxy](../ble-dumpcap-source/hci-control.json).
That earlier receipt did not retrospectively measure the original five positive
packets' HCI configuration. The failed native-source diagnostics used different
properties `0x0010`, map `0x01` and nonzero MaxEvents; comparing these routes does
not isolate any one of those differences. The helpers request only owned advertising setup/removal and read-only monitor
access; they issue no controller event-mask, power, reset, discovery or pairing
commands.

The [source receipt](source.json) records three requested 120-second episodes with
20-second OFF gaps, accepted removals, no premature releases and bus disconnect.
The actual initial OFF bracket was **20.236 seconds**. The final payload arrived
**38.404 seconds after observed source process-group closure**, which followed
its recorded bus disconnect. Monitor readiness preceded receiver readiness;
monitor completion took **481.310 seconds** and its exact owned container was
removed. Powered=true and ActiveInstances=0 were observed before and after.
The [orchestration receipt](orchestration.json) retains the actual timestamps,
helper hashes and selected installed firmware part hashes.

These are control-plane observations. Advertising intervals, source sessions and
received snapshots are **not emitted-event counts**. Both emission denominators
remain null; no packet detection rate is reported. Unknown monitor loss prevents
an assertion of complete HCI observation.

## Full replay and phase joins

The existing locked Task decoder replayed every waveform with rate 16,000,000,
bits 8, samples 16,380, channel 37, translation −1,000,000 Hz and the unchanged
blind refinement bounds. No search expansion or known-marker bit repair occurred.
The subsequent Task report used the **whole command-start through payload-receipt
bracket**, with the predeclared **one-second guards**:

| Guarded phase | Snapshots | Verified owned packets |
| --- | ---: | ---: |
| Initial OFF | 52 | 0 |
| ON episode 0 | 319 | 0 |
| OFF after episode 0 | 48 | 0 |
| ON episode 1 | 320 | 0 |
| OFF after episode 1 | 49 | 0 |
| ON episode 2 | 321 | 0 |
| Final OFF | 103 | 0 |
| Transition guards excluded | 39 | 0 |

[Phase classification](phase-classification.csv) retains every bracket and label;
[decode-summary.json](decode-summary.json) records fixed settings, decoder/input
provenance, full result hashes, runtime and counts. Five captures had unverified
access-address candidates: 549, 748 and 751 in ON episode 1; 826 in ON episode 2;
and 1166 in final OFF. Their outcomes were invalid-header, truncated or CRC-failed.
None is attributed to the owned source. Detailed failed hypotheses and all raw
waveforms stay private. Candidate counts are not packet counts.

## Recovery and next decision

The [restoration receipt](restoration.json) verifies all **4,194,304 restored
bytes** against the preserved original SHA-256
`6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`, followed
by the expected original application, SDK and both GPIO messages on reset boot.
The owned UART groups were confirmed closed before restoration. This receipt
proves reset recovery and makes no electrical power-cycle claim.

The current control did not reproduce an owned packet, so the conditional direct
source-limiter Trial B is not run. The prospective
[known 10-bit profile control](../../research/ble-next-trial.md) uses the exact
previously successful capture-103 receiver cell. It changes precision, filter and
gain together and will not establish which parameter matters. No reception,
calibration or counted-source requirement is accepted by this null result.

Sources: the [pinned ESPARGOS receiver](https://github.com/ESPARGOS/esp-sdr/tree/550fadea4d00a9e26ce921c5832167becb3dc20c),
[BlueZ advertisement API](https://github.com/bluez/bluez/blob/master/doc/org.bluez.LEAdvertisement.rst),
and the [libpcap monitor backend](https://github.com/the-tcpdump-group/libpcap/blob/master/pcap-bt-monitor-linux.c).
Decoder protocol/vector sources are retained in the decode summary. Software
and private-input evidence, rather than a screenshot, support these narrow results.
