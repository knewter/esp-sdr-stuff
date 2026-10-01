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

## Visual plan

[Experiment flow and provenance](docs/design/the-receiver-can-observe-and-decode-short-bursts/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.
