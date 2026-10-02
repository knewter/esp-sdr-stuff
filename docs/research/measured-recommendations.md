# What these receivers can usefully do

Checkpoint: 2026-10-02 UTC. Use the attached RTL-SDR Blog V4 for continuous
HF/VHF/UHF work. Use this original ESP32 for experimental short snapshots
and repeated 2.4 GHz signal observation, with verified owned BLE packets and explicit limits.
Its installed UART path misses almost all elapsed RF time. FPGA work should
start with a small verified data-processing or buffering boundary.

## Actual measurements

The [V4 transport tests](docs/evidence/rtl-continuity/README.md) ran for at least
65 seconds each at 1.024, 2.048, 2.4 and 2.56 MS/s. Three reported no
discontinuities; the 2.048 trial reported one gap of at least 80 bytes. The
8-bit incrementing test pattern can miss losses of complete 256-byte cycles;
zero reported loss is not an absolute loss-free guarantee. These are USB
transport tests, separate from RF reception and calibrated clock measurements.

The [ESP32 baseline](docs/evidence/snapshot-baseline/README.md) passed CRC/count
checks on all 600 snapshots at advertised 16/40/80 MS/s in both 8- and 10-bit
formats. Full snapshots take about 361/451 ms to deliver through CP2102 at
921,600 baud. Their nominal listening windows span 1.024/0.410/0.205 ms.
Measured-series nominal coverage ranges from 0.045% to 0.281%. Those gaps
rule out using this installed path as a continuous wideband recorder.

| Application | V4 | This ESP32 | Current proof and practical choice |
|---|---|---|---|
| Broadcast FM, narrowband VHF/UHF, HF listening | Manufacturer's direct coverage about 0.5–1766 MHz; continuous narrow streams | Normal Wi-Fi-band receiver path; unrelated lower-frequency commands unvalidated | Choose V4. Actual no-FEC RDS identifies WXJC at 101.1 MHz; the current path works for that station. The user confirms the current dipole; its geometry and other-band performance remain unverified. |
| Persistent recording of events in a roughly 1–2 MHz channel | Host-delivered stream demonstrated at the tested rates, with the stated loss limits | About 0.36–0.45 s between full snapshot deliveries | Choose V4 when the target is in its direct band. The ESP path is unsuitable for exhaustive event counts. |
| Direct 2.4 GHz spectrum research | Requires external downconversion; no such common path is verified | Raw snapshots and on-device FFT output physically demonstrated; five complete owned BLE packet windows yield CRC-valid, exact known ADs | ESP adds access to a different band. A successful command or uncalibrated trace does not validate every tuning point. |
| Complete BLE legacy advertising waveform | Cannot directly tune 2.4 GHz in normal V4 configuration | A 16 MS/s full snapshot nominally fits a packet; 80 MS/s's 205 µs does not fit the owned 256 µs minimum packet | ESP is a repeated-packet experiment, not a reliable sniffer. Five known-marker packets are decoded offline; independently counted emissions and reliable repeated interception remain open. |
| Occasional wide instantaneous observations | A few MS/s delivered; coverage outside the selected channel needs sequential tuning | Advertises much wider instantaneous sample rates, followed by long transfer gaps | ESP may reveal repeated wide events. ADC rate does not establish analog usable bandwidth or guarantee interception of a particular event. |
| Transmission | Receiver design | No transmit trial implemented or verified in this evaluation | No TX capability accepted for either setup. |
| FPGA processing | Can process the host's verified narrow stream if an explicit interface is built | A future route must extract data through a separately verified interface | Begin with synthetic-pattern transport and a bounded DSP task. Neither owned FPGA has passed local bring-up. |

## Frequency and application sources

The [V4 manufacturer design description](https://www.rtl-sdr.com/rtl-sdr-blog-v4-dongle-initial-release/)
documents its internal HF upconverter and HF/VHF/UHF input division. This is
manufacturer coverage, not a local sweep of every frequency. The
[actual FM evidence](docs/evidence/rtl-fm-survey/README.md) is a five-second
uncalibrated ambient capture; the measured 19 kHz feature is consistent with
a stereo pilot. [Subsequent no-FEC RDS decoding](docs/evidence/rtl-rds-trial/README.md)
now identifies WXJC with repeated directly valid PI blocks and public RadioText;
[independent replay](docs/evidence/rtl-rds-independent-review/README.md) reproduces
both input trials and checks [the station-owned frequency](https://www.wxjcradio.com/).
A [fresh trial with the current user-reported dipole](docs/evidence/rtl-dipole-rds/README.md) again identifies WXJC: 287 directly valid PI blocks with FEC disabled. [Fresh independent replay](docs/evidence/rtl-dipole-independent-review/README.md) reproduces its output. Antenna model, dimensions, orientation and calibrated sensitivity remain unverified.

[Pinned ESPARGOS controls](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/docs/rx-controls.md)
and [capture code](https://github.com/ESPARGOS/esp-sdr/blob/550fadea4d00a9e26ce921c5832167becb3dc20c/main/targets/esp32/receiver.c)
describe the modem path and experimental filters. The physical protocol
advertises commands from 100–6000 MHz; this evaluation has not established
usable reception or PLL lock across that range. Wider ADC sampling also does
not independently validate a flat 80 MHz analog passband.

## Demonstrated ESP application

[Four actual 8-bit captures](docs/evidence/ble-owned-decoding/README.md) and
[one 10-bit capture](docs/evidence/ble-controls-decoding/README.md) yield complete
owned BLE packets with protected-PDU CRC and exact independently chosen AD.
Public plots omit phase and addresses; private originals are available for local
independent replay. All four initial packets occurred in the third source-ON
episode, so the paired trial does not establish three-repeat reliability.
Preamble/access hard-decision errors, source API/wire-type mismatch, uncalibrated
frequency offsets and the missing 100-emission denominator remain explicit.
This is a useful DSP experiment and specific reception proof, with large gaps.

A [physical Bluetooth monitor](docs/evidence/ble-dumpcap-source/README.md) now verifies accepted source settings. [Three finite source diagnostics](docs/evidence/ble-counted-source-smoke/README.md) accept commands but supply no actual completed-event count. [Timer diagnostics](docs/evidence/ble-duration-source-diagnostics/README.md) now observe termination events with an actual zero completed-count field. A [ten-episode RF discriminator](docs/evidence/ble-zero-counter-rf/README.md) finds no CRC-valid owned packet in 262 retained snapshots; this null is inconclusive and does not negate the earlier five verified packets. The reporting protocol is ready; receiver hit-rate trials remain pending on a verified source count independent of the ESP decoder.

## FPGA decision so far

[Inventory and calculations](docs/evidence/fpga-inventory/README.md) identify
the official Forgix design as RP2354 plus Trion T8. Its RP2354 USB 1.1 wire
ceiling is 1.5 MB/s before overhead; raw 80 MS/s, packed 10-bit I/Q requires
200 MB/s. An FPGA cannot make that USB endpoint carry the full stream. A
bounded event detector, FFT reduction, decimation or small pattern buffer is
a more plausible boundary, pending actual wiring, clocks and transport tests.
The T8's total documented embedded memory is only 15 KiB; at 200 MB/s its
ideal all-memory buffer would last 76.8 µs, before allocating logic resources.

The host PCIe device is enumerated at Gen3 ×4, but its board markings,
programming interface, clock and driver/data path remain unverified. A BAR
size is not a DRAM capacity measurement. A fast connector does not establish
a working ADC-to-host path. The eSpDR S3-plus-FPGA implementation targets
different ESP silicon and cannot be assumed to work by attaching either FPGA
to this LX6 board.

## Remaining decisions

The [user inventory](docs/evidence/user-equipment-inventory/README.md) reports no external RF equipment. A same-signal sensitivity ranking is deferred; a common path, mixer/LO, filters, losses and calibration would need to be recorded first. Forgix is reported attached but remains unidentified in USB; physical revision, clock and wiring remain unknown. [Preserve-first bring-up](docs/research/forgix-bringup.md) is prepared. Recommendations above describe the
measured transport envelope and sourced hardware limits; unverified
applications and incomplete proposal tasks remain open. AtomVM is deferred
by user and excluded from the current goal.
