## Why

Upstream lists our chip as supported, but we have not captured a single RF sample on this board. A repeatable baseline must establish what actually works before application claims.

## What Changes

- Pin and build the original-ESP32 ESP-SDR target with its prescribed SDK.
- Install only after preservation; query firmware capabilities and record supported settings.
- Collect CRC-checked snapshots and measure acquisition/transfer gaps at 16, 40 and 80 MS/s.

## Capabilities

### New Capabilities

- `radio/snapshot-capture`: A reproducible raw-I/Q and browser-spectrum baseline on the actual LX6 board.

### Modified Capabilities

None. Existing identity records remain factual baselines.

## Impact

Physical ESP32, host UART and its existing antenna; controlled 2.4 GHz source used later.

Dependencies: [the board can be restored after an sdr trial](../2026-10-01-the-board-can-be-restored-after-an-sdr-trial/proposal.md)

## Non-goals

No continuous stream claim, FPGA port, TX implementation or calibrated sensitivity claim.

## Decision gate

At least 100 CRC-checked snapshots per advertised rate with failures and timestamps counted; 60 seconds of browser display with gaps documented.

## Evidence and sources

Baseline: [board-identification](docs/evidence/board-identification/README.md). Sources: [primary-source register](docs/research/source-index.md).
