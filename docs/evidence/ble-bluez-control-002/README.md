# The known 10-bit receiver profile also has no verified owned packet

Recorded 2026-10-02. Trial C completed **997 CRC- and count-valid snapshots**,
three full owned-source episodes, monitored cleanup and verified original-flash
restoration. The predeclared full decoder replay found **zero verified owned
packets and zero CRC-valid foreign packets**. This retained null result does not
establish an emission count, missed-packet rate or inability to receive BLE.

The receiver used the previously successful capture-103 cell: requested LO
**2401 MHz**, nominal **16 MS/s**, **16,380 I/Q pairs**, **10-bit** components,
filter **20 MHz**, manual gain **48** and UART **921600 baud**. Actual commands and
ACKs appear in [receiver.json](receiver.json). This control changes precision,
filter and gain together relative to [Trial A](../ble-bluez-control-001/README.md);
it cannot identify a causal receiver parameter. Gain 48 is neither a calibrated
power setting nor a demonstrated optimum. The earlier
[complete capture-103 packet](../ble-controls-decoding/README.md) remains valid
historical evidence; the fresh control did not reproduce it.

Each private file contains **40,950 bytes**, total **40,827,150 bytes**. Every
saved file was checked against the exact [capture CSV](captures.csv): SHA-256,
expected and actual CRC32, returned count, length and ordered complete
command/header/payload timestamp bracket. [Input verification](input-verification.json)
records the aggregate; raw I/Q stays private.
Each snapshot spans only **1.02375 ms nominally**. Command, transfer and host
work separate the windows; the 460-second session is not continuous RF capture.
Unobserved intervals cannot be classified as decoder failures or missed emissions.

## Actual source and completed schedule

The [sanitized monitor](monitor.json) records the same source configuration in
all three episodes and **15 matching successful command completions**:

| Observed HCI field | All three episodes |
| --- | --- |
| Advertising handle | 1 |
| Event properties | `0x0013` |
| Primary channel map | `0x07` |
| Requested minimum/maximum interval | 20 ms / 20 ms |
| Primary/secondary PHY fields | 1 / 1; legacy LE1M profile |
| Manufacturer AD | Exact owned 16-byte marker |
| Duration / MaxEvents | 0 / 0 |

These fields match Trial A and the [earlier monitored BlueZ proxy](../ble-dumpcap-source/hci-control.json).
That proxy did not retrospectively measure the original positive packets' HCI
configuration. Prior native counter diagnostics used properties `0x0010`, map
`0x01` and nonzero MaxEvents. This comparison does not isolate their differences
or establish a controller defect. These helpers issued no global event-mask,
power, reset, discovery or pairing command.

The [source receipt](source.json) records three accepted 120-second episodes
with 20-second OFF gaps, no premature release, accepted removals and bus
disconnect. The actual initial OFF bracket was **20.692 seconds**; the final
payload arrived **38.592 seconds after source process-group closure**. Monitor
readiness preceded receiver readiness; its completed duration was **481.378
seconds**, with its owned container removed and producer reaped. Powered=true
and ActiveInstances=0 were observed before and after. [Orchestration](orchestration.json)
retains actual timestamps, executed helper hashes and installed part hashes.

Source configuration acceptance, commanded intervals and sessions are
control-plane evidence, not measured RF cadence or emitted-event counts.
Unknown monitor loss also prevents a complete-HCI-observation claim. Both
emission denominators remain null and no detection rate is reported.

## Complete fixed-bound replay

The locked Task decoder replayed every waveform using rate 16,000,000, bits 10,
samples 16,380, channel 37, translation −1,000,000 Hz and the unchanged blind
refinement bounds. No search expansion, known-payload timing training or bit
repair occurred. Replay took **19.809 seconds**. The subsequent Task report used
whole command-start through payload-receipt brackets with the predeclared
**one-second guards**:

| Guarded phase | Snapshots | Complete verified owned packets |
| --- | ---: | ---: |
| Initial OFF | 42 | 0 |
| ON episode 0 | 254 | 0 |
| OFF after episode 0 | 38 | 0 |
| ON episode 1 | 256 | 0 |
| OFF after episode 1 | 38 | 0 |
| ON episode 2 | 254 | 0 |
| Final OFF | 82 | 0 |
| Transition guards excluded | 33 | 0 |

[Phase classification](phase-classification.csv) retains every label and timing
bracket. [Decode summary](decode-summary.json) includes source/input/decoder/
reporter hashes, unchanged search settings and private full-result hashes. Ten
captures contain unverified access-address candidates; their outcomes are
CRC-failed, truncated or invalid-header, including one CRC failure during final
OFF. None is attributed to the source. Detailed failed hypotheses remain private.

The tightened offline reporter counts and plots only protected CRC24 plus whole
owned AD, retained protected-PDU hash and an explicitly complete, finite nominal
preamble-through-CRC window within the snapshot, consistent with its selected
symbol period. Duplicate access-address hypotheses count once. A CRC-valid
coarse candidate without those bounds is retained separately as waveform
unverified. Packet type and AA/preamble diagnostics must be retained; conflicting
protected-PDU hashes in one access-address cluster are excluded. This changes no
decoder search or acquisition behavior; there are no
CRC-valid candidates in this dataset. The five earlier complete owned packets
still pass the stricter guard; [reporter verification](reporter-verification.json)
retains their golden input hashes and the focused software-check result.

Reproduce the two offline steps with fresh private output paths:

```sh
nix develop --command task decode:ble -- --input .scratch/ble-bluez-control-002/iq --output .scratch/ble-bluez-control-002/replay-next.json --rate 16000000 --bits 10 --samples 16380 --channel 37 --frequency-translation-hz -1000000 --refine
nix develop --command task report:ble -- --decoder .scratch/ble-bluez-control-002/replay-next.json --captures .scratch/ble-bluez-control-002/receiver/captures.csv --source .scratch/ble-bluez-control-002/source/results.json --private .scratch/ble-bluez-control-002/iq --output .scratch/ble-bluez-control-002/report-next
```

## Verified recovery and next decision

The [restoration receipt](restoration.json) verifies all **4,194,304 restored
bytes** against original SHA-256
`6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`, followed
by the expected original application, SDK and both GPIO messages on reset boot.
All owned UART groups closed before restoration. This proves reset recovery;
electrical power removal was not measured.

Fresh RF-positive control remains a prerequisite for the prospective direct
source comparison. Trial C is null, so that conditional Trial B is withheld.
Neither calibration nor counted-source requirements are accepted here. Further
RF diagnosis needs a prospectively declared receiver/placement control or an
independent RF reference; this result does not justify widening decoder bounds.

The official [Core 6.2 termination event, §7.7.65.18](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html#UUID-b7eedd85-4369-f88f-7872-7278f7778cd2)
applies to legacy and extended advertising: nonzero MaxEvents makes the completed
count meaningful on duration or event-limit termination; MaxEvents=0 requires
count zero. Duration ends with status `0x3c`, the event limit with `0x43`.
[Enable semantics, §7.8.56](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html#UUID-d05d4cfe-f0b5-b0e2-1a63-672c960dc088)
start duration at the first advertising event. Its special high-duty directed
connectable case does not apply to undirected nonconnectable properties `0x0010`.
[Extended parameter ranges, §7.8.53](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html#UUID-2d5f3e1f-6666-baa9-dcc2-5d8af3709dac)
allow the requested 20 ms interval, including legacy `ADV_NONCONN_IND`; these
ranges are not proof of measured cadence. The official
[HCI test specification p37](https://files.bluetooth.com/wp-content/uploads/dlm_uploads/2025/05/HCI.TS_.p37.pdf),
HCI/HFC/BV-19-C, printed page 125, explicitly exercises legacy properties
`0x0010` with Duration=0, MaxEvents=8 and eight `ADV_NONCONN_IND` PDUs. Thus the
specification does not generally exempt legacy advertising from the limit.
These normative rules do not explain the earlier zero-count observations.

Receiver source: [pinned ESPARGOS firmware](https://github.com/ESPARGOS/esp-sdr/tree/550fadea4d00a9e26ce921c5832167becb3dc20c).
Source control: [BlueZ advertisement API](https://github.com/bluez/bluez/blob/master/doc/org.bluez.LEAdvertisement.rst).
Monitor transport: [libpcap Bluetooth monitor backend](https://github.com/the-tcpdump-group/libpcap/blob/master/pcap-bt-monitor-linux.c).
Protocol and published vector links remain in the decode summary.
