# Forgix host toolchain evidence

Captured 2026-10-02 using the integrated `.#forgix` Nix shell and Task commands.
This is host setup evidence. No USB, serial, JTAG, PCI or DMA device was opened;
no MCU firmware or FPGA configuration was replaced.

- [Sanitized host receipt](host-receipt.json): runtime versions, fixed source
  revisions, CLI-help outcomes, generated RTL hash, built output NAR hashes,
  local installer-search scope, and explicit absent-vendor/unknown-board gates.
- [Nix host-check output](host-check.txt): real imports, RTL generation and
  **17 passing upstream host tests**. Four local fail-closed guard tests also
  passed inside the integrated Forgix shell.
- [Setup and official license/download instructions](../../research/forgix-toolchain.md).

The FHS runtime wrapper was built and executed. It correctly refused an absent
`LITEX_ENV_EFINITY` with exit 2. No Efinity binary compatibility or license
compile has been tested. The current result is `host_ready`, with
`vendor_cli_verified`, `license_compile_verified` and `gateware_ready` all
false. FPGA grade, oscillator frequency and board revision are still unknown.

The filename-only local search found no installer, compiler or matching license
candidate within its recorded scope. It did not inspect account credentials,
license contents or every filesystem; a support account may already exist.

These tests do not prove register communication with the attached board,
sustained SPIBone/IQ throughput, RF reception, or a useful SDR FPGA pipeline.
The original [factory MCU preservation evidence](../forgix-preservation/README.md)
remains the prerequisite for any later firmware or gateware trial.

## October 3: provisional Forgix candidate compilation

This follow-up supersedes the initial absent-vendor checkpoint above for host
readiness. Nix/Task now compile an explicitly provisional **T8F49/I2, 32 MHz,
passive-SPI x1** SPIBone candidate with identifier ROM, counter and scratch
registers. LED chaser, edge demos and scope are disabled. Physical parameters,
programming admission and SPI turnaround remain **false**.

Attempt001 failed after real Interface Designer generation, before synthesis
or bitstream creation: its guard expected the generic bidirectional GPIO name.
The retained failure was corrected against Efinity's actual lowered F2 name;
the corrected guard also binds the consumed ROM file and exact private XML
input paths. **Fourteen focused Nix tests pass without skips.**

Actual002, source `fdde1e55a3e68c074611af70b96081849803e14c`, completed in
**36.74 seconds**, exit 0, with ordered **map/interface/pnr/pgm PASS** and a
fresh **520,140-byte hex**. `pgm` generates files; no programmer was invoked.
The receipt attests owned process-group closure and private-file verification;
no hardware was opened. Exact private receipt SHA-256:
`a15c0dd5018e57b19e1a3d645375fc50f1f1e2110933e48e43f807412e7ffec0`.
Bitstream SHA-256:
`ac66a44110171a40626da3bb633568587733e40661a4cef4567ee6edcf357985`.
Helper SHA-256:
`2d043303ef25b32ff5f92242ae1231555b0c32d2aaee401b0c0de33fcd43822b`.

Final package assignments are only **B4 clock, G3 CS, F3 SPI clock and F2
bidirectional data**. The backend's unused original MOSI declaration is absent
from the placed interface. Reports use 529 logic elements, one RAM block and
zero multipliers. The provisional I2 model reports internal 32 MHz setup slack
+7.701 ns and hold slack +0.643 ns. External SPI I/O delays are unconstrained;
these numbers do not qualify actual clock frequency or SPI performance.
Compiler warnings remain retained, including width truncations and the ROM
driver warning; the mapped ROM initialization matches the identifier bytes.
T8F49 ignores the requested configuration CRC option because programming CRC
is unsupported. No physical register readback or configuration integrity was
demonstrated.

[Photo/BOM and factory-pin review](../fpga-inventory/README.md) explains the
grade conflict and RP GPIO3 ownership blocker. Independent review of the
corrected source passed 14 tests plus ten independent probes; receipt SHA-256:
`d5bc4212b37b42abb9faaf3dccc079db3b4967f4315faac4f75fa5a6a09e2776`.
Independent actual-artifact audit hashes all 72 retained files and verifies
stages, fresh output, generated inputs, private modes and final pin reports;
receipt SHA-256:
`768539bc74b6be3bb0ce9eea878af8947e81c624399543c6a2b7e05017800146`.
Process closure is the parent receipt's attestation, not an independent PID
survey. Projects, vendor logs, bitstreams and photos stay
ignored and private. The existing verified-parameter build path is unchanged;
the FPGA feasibility proposal remains **1/5 tasks complete**.
