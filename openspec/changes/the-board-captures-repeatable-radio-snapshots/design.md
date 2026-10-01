## Context

See [proposal](proposal.md) for the problem and scope. The hardware identity is recorded separately from untested reception and transport behavior.

## Goals / Non-Goals

**Goals:** A reproducible raw-I/Q and browser-spectrum baseline on the actual LX6 board.

**Non-Goals:** No continuous stream claim, FPGA port, TX implementation or calibrated sensitivity claim.

## Decisions

Start with upstream original-ESP32 firmware rather than the S3-only eSpDR implementation. Use the SDK revision recorded in firmware-targets.json. Keep hardware ADC rate separate from host delivery.

The host records revisions/settings/results; firmware owns modem and memory access; an FPGA, if selected, owns only its explicitly measured transport/processing boundary.

## Risks / Trade-offs

UART bridge and USB path may reject high baud rates. Start conservatively and measure. RF commands accepting a frequency do not prove PLL lock.

## Validation and decision

At least 100 CRC-checked snapshots per advertised rate with failures and timestamps counted; 60 seconds of browser display with gaps documented.

Build uses the SDK revision from the pinned firmware-targets.json, then `idf.py -B build-esp32 -DIDF_TARGET=esp32 -DSDKCONFIG=sdkconfig.esp32 -DSDKCONFIG_DEFAULTS=sdkconfig.defaults.esp32 build`. Protocol replies and a future CRC-checking host harness prove the physical capture tasks.

## Visual plan

[Experiment flow and provenance](docs/design/the-board-captures-repeatable-radio-snapshots/README.md). This is a design illustration, not measured radio evidence.

## Primary references

[Source register](docs/research/source-index.md) contains pinned repository links and limitations.
