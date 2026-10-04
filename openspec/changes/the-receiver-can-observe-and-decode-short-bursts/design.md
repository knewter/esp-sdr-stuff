## Context

See [proposal](proposal.md) for the problem and scope. The hardware identity is recorded separately from untested reception and transport behavior.

## Goals / Non-Goals

**Goals:** Decide which interference, educational DSP and short-burst applications are useful on this board.

**Non-Goals:** No whole-session Bluetooth capture, guaranteed packet logging, continuous audio or encrypted-content access.

## Decisions

Make spectrum observation the first application. A 16,380-sample window is roughly 0.205/0.410/1.024 ms at 80/40/16 MS/s; choose waveforms only after duration and bandwidth fit are checked. Offline decoding of a captured burst is distinct from reliable live reception.

The host records revisions/settings/results; firmware owns modem and memory access; an FPGA, if selected, owns only its explicitly measured transport/processing boundary.

## Risks / Trade-offs

Packet timing, frequency hopping and transfer gaps can dominate detection. Failed decoding may reflect truncated data rather than bad demodulation.

## Validation and decision

At least 100 deliberately emitted repeat events with ground-truth counts and capture hit rate; a decoding claim includes a complete waveform and verified payload.

Physical proof: 100 counted emissions plus capture timestamps and a saved waveform; offline proof: run the selected decoder on the pinned capture and compare output to the known payload. No decoder or protocol support is assumed in advance.

The [counted-trial protocol](docs/research/ble-counted-trials.md) predeclares three 255-event repetitions using a single-channel legacy source and an actually observed controller termination counter, independently of ESP decoding. It requires full waveform replay, exact known data and explicit unresolved outcome bounds. Controller-reported completed events must remain distinct from independently measured radiated RF emissions.

[Three source-only diagnostics](docs/evidence/ble-counted-source-smoke/README.md) accepted parameters, data and finite enable commands but produced no termination count. They are not receiver trials and close neither event-observation task. The source counter must pass before the predeclared receiver trials run; no guessed event-mask overwrite or arithmetic interval-derived denominator is allowed.

## Visual plan

[Experiment flow and provenance](docs/design/the-receiver-can-observe-and-decode-short-bursts/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.

## Timer diagnostic boundary

Subsequent [timer diagnostics](docs/evidence/ble-duration-source-diagnostics/README.md)
observe `0x3C` termination with completed count zero; the [prospective RF
discriminator](docs/evidence/ble-zero-counter-rf/README.md) is inconclusive.
These diagnostic captures are separate from the three counted receiver trials.
Original counting and acceptance criteria remain unchanged. A recorded usable
source denominator is still required.

The [bounded register observation](docs/evidence/receiver-register-observation-002/README.md)
completes 20 valid snapshots and 81 ordered sampled stages with full original
restoration. Selector 48 / bit23=1 throughout narrows a sampled configuration-field
mismatch explanation for that run; it does not decode a packet, qualify source
counts or explain the fresh SDR nulls. The first supervisor failure is retained.
Trial B remains withheld until its original fresh SDR-positive prerequisite.

The [matched ten-bit controls](docs/evidence/ble-matched-gain-001/README.md)
now reproduce one fresh manual48 owned packet with independently verified
protected CRC, whole AD and complete waveform window. All 1,994 inputs and both
full restorations pass [independent replay](docs/evidence/ble-matched-gain-independent-review/README.md).
Hardware gain retains zero owned and one redacted foreign CRC packet. The source
remains uncounted, three-response proof remains incomplete, and this profile
does not replace Trial B's original eight-bit/BW12/hardware-gain prerequisite.

## Extended primary-header preparation

The [reviewed primary preparation](docs/evidence/ble-primary-preparation/README.md)
adds a separate zero-data source profile and strict CRC-valid extended primary
header parser. Eighty-nine scoped host checks pass after a peer-reviewed
auxiliary-offset timing correction. This is preparation, not new reception.
Missing AdvA, ADI-only identification and auxiliary AD cannot establish ownership.
Zero data does not force a particular primary layout or AUX omission.

Controller-completed extended events remain distinct from independently counted
primary RF transmissions, including permitted event/PDU omission. Those historical
monitor records omit some requested HCI fields; do not claim their independent
physical verification. Original emitted-count, full waveform, three-response
and Trial B prerequisites remain unchanged; no task is checked by these tests.
