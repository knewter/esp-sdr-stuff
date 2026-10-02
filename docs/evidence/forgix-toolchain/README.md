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
