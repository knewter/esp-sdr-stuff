# Fresh manual-gain SDR reception is independently reproduced

Recorded 2026-10-02. Two prospectively declared 460-second controls retain
**1,994 transport-valid snapshots** with zero integrity failures. Manual gain
48 contains **one independently verified complete owned BLE packet**; hardware
AGC contains zero owned packets and one foreign CRC-valid packet, with foreign
data redacted. Both restore all 4,194,304 original flash bytes and the expected
reset boot. This is partial fresh reception evidence, not a gain ranking,
three-cycle response, emitted count or detection rate.

The [protocol](../../research/ble-matched-gain-protocol.md) and
[independent preflight](../ble-matched-gain-preflight/README.md) fix the same
uninstrumented UART921600 firmware, LO 2401 MHz, requested bandwidth 20 MHz,
nominal 16 MS/s, ten-bit components and 16,380 I/Q pairs. Requested gain mode
changes from MANUAL48 to HARDWARE, in that order. Separate restarts, calibration,
time and foreign interference remain confounds. Physical placement and antenna
setup were held fixed; no distance or calibrated gain is assumed.

## Complete current packet

Manual capture **48** has waveform SHA-256
`f5a34238bff52380401ea4503153f1cfc92b27baf33c57f095588a53ad30c967`,
different from all five historical positive payloads. The protected PDU hash is
`177ba70ae0be7ffff890d04b3214f18a46cfe85e47b485bf82dd5c534c53aa45`:
type 0 / ADV_IND, length 22, complete owned 16-byte manufacturer AD,
AA/preamble errors 1/1 and one unique CRC-valid receiver hypothesis. The nominal
preamble-through-CRC window is samples **291.84–4392.96**, wholly inside the
16,380-pair snapshot. The full command-to-payload bracket lies in guarded ON
episode 0; its start is 1.087941475 seconds after accepted registration.

The [independent actual review](../ble-matched-gain-independent-review/README.md)
replays all captures and separately re-slices this original waveform using
AA-only training, independent signed packing, whitening and reflected CRC24.
No decoder search expansion, payload training or repair occurred.
[Packet amplitude and complete window](manual-owned-envelope.svg) show actual
measured data; amplitude is uncalibrated ADC code power.

## Source phases, integrity and recovery

| Guarded phase | Manual snapshots / owned packets | Hardware snapshots / owned packets |
| --- | ---: | ---: |
| Initial OFF | 43 / 0 | 42 / 0 |
| ON 0 | 256 / 1 | 252 / 0 |
| OFF after 0 | 39 / 0 | 39 / 0 |
| ON 1 | 259 / 0 | 241 / 0 |
| OFF after 1 | 38 / 0 | 39 / 0 |
| ON 2 | 259 / 0 | 258 / 0 |
| Final OFF | 83 / 0 | 81 / 0 |
| Transition guards excluded | 33 / 0 | 32 / 0 |

The [manual](manual-captures.csv) and [hardware](hardware-captures.csv) capture
CSVs retain every complete timing bracket and payload hash; all 40,950-byte raw
files pass length, sample count, SHA-256 and expected/actual CRC32 checks. Raw
I/Q and original flash remain private. [Manual](manual-phases.csv) and
[hardware](hardware-phases.csv) labels use unchanged whole-response brackets
with one-second guards. Each nominal snapshot spans only 1.02375 ms; transfer
and command gaps make these separated windows, not continuous reception.

Both sanitized monitors ([manual](manual-monitor.json),
[hardware](hardware-monitor.json)) show three identical source configurations:
handle 1, properties `0x0013`, map 7, 20 ms min/max, LE1M, complete owned AD,
Duration 0 and MaxEvents 0. Each has fifteen successful command/ACK pairs,
including scoped disable/remove. The [source](manual-source.json)
[receipts](hardware-source.json) prove three 120-second episodes, intervening
OFF intervals, no premature release and bus disconnection. Actual initial OFF
is 20.672 / 20.843 seconds; final payload tails after source group closure are
38.694 / 37.274 seconds. All owned groups and monitor containers close.

[Manual restoration](manual-restoration.json) and
[hardware restoration](hardware-restoration.json) match original SHA-256
`6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`
and expected application/SDK/GPIO reset boot. Electrical power removal is not
measured. [Results and exact input hashes](results.json) bind the private full
decodes, phase reports and orchestration; receiver acknowledgements are retained
for [manual](manual-receiver.json) and [hardware](hardware-receiver.json).

## Scalar comparison and decision

[Actual code statistics](code-statistics.svg) retain every whole-response
bracket and commanded source span, with no smoothing. The
[frozen scalar replay](scalar-results.json), [input verification](scalar-verification.json)
and [method preflight](scalar-preflight-review.json) retain centered AC,
signed endpoints, integrated Hann +1.5 to +2.5 MHz code power, block-32 ratios
and guarded ten-second edges. Source-enable target-band ratios are
**1.100, 1.089, 0.824** for manual and **5.199, 1.275, 0.735** for hardware.
Neither has three repeated increases; hardware band power also drifts in OFF
phases. These statistics do not establish owned-source causality, calibrated
gain, SNR or absence of RF. Gain queries occur before settings; ACKs establish
requested software mode only.

The owned packet reproduces a working fresh ten-bit SDR example. Original
three-response RF and counted-event tasks remain open. Trial B still requires
its original current eight-bit/BW12/hardware-gain Trial A control; this different
profile does not silently replace that prerequisite. No rates are reported
without an actual emitted denominator. Earlier failed/null controls remain
unchanged and available.

Replay uses the existing locked `task decode:ble` with rate 16000000, bits 10,
samples 16380, channel 37, translation -1000000 and refinement, then
`task report:ble` against the corresponding source/CSV/private IQ paths.
The [pinned firmware](https://github.com/ESPARGOS/esp-sdr/tree/550fadea4d00a9e26ce921c5832167becb3dc20c)
and [source register](../../research/source-index.md) retain primary references.
