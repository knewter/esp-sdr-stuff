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

## Reconnect and guarded candidate003

After reconnect, the preserved USB identity and two HELLO/STATUS pairs passed
a five-second stability check. A later fresh-preservation attempt timed out
at the initial serial DTR control request, before ROM or picotool operations;
its worker was closed and the failure remains retained. Following the user's
second reconnect, dedicated preservation002 passed in **43.23 seconds**:
two fresh **2,097,152-byte** reads match the original
`72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4`,
separate device verification passes, and the factory application returns.
All six picotool operations exit 0 with owned closure; no flash write, RAM
diagnostic load or FPGA programming occurred. Private session SHA-256:
`ec9bb8ff0f1fb18601c9309c1b6a8da72f1e4b4f54bae97c2aef52df6a9757fa`.
Earlier CI-shell/missing-SDK/timeout refusals occurred in host preflight and
opened no device; exact pinned dependencies were restored through Nix.

Source `60ba10c686db5c039a10c077ec4f0fa1e2465cb9` adds a contained wrapper
around pinned SPIBone: 32 stable synchronized idle cycles before activation,
64 cycles after request capture plus a new falling-clock handoff before
output/bus admission, and immediate raw-CS output/request suppression.
Eight asynchronous Migen simulations and 15 candidate tests pass. Independent
source review adds seven response/phase probes. These prove the digital model
under its stated RP contract; unsampled glitches and actual high-Z/timing
are unqualified. The RP bridge is still required.

Actual003 completes map/interface/pnr/pgm in **33.93 seconds**, exit 0,
producing a fresh **520,140-byte** hex. Receipt SHA-256:
`09e88d3c7a7fac53b6e8f40b974ad1ea42cf84ff0e98883cf1937f7f2ecfb576`.
Hex SHA-256:
`2c74a218e8bc654aafae74cff9ba4ae4cb7eb11b657ab6ab7a540044868140b1`.
All physical/programming/RP-contract verification flags remain false.
Candidate002 stays immutable and unadmitted. Independent actual003 review
checks all 72 retained files and the placed guard logic: exactly four assigned
pins, 566 logic elements, one RAM, internal setup +7.421 ns/hold +0.642 ns at
the provisional 32 MHz/I2 model. External SPI delays remain unconstrained.
Source-admission receipt SHA-256:
`8de3f735ff41625dddd94d1409bcb5d0ef96af9c8b3ef2c04a9059d3b8de75e8`.
Actual-artifact review SHA-256:
`d5c056ea22e17ecea1e003539134511dc11437a2af8b212ba0568611bd8ec238`.
The failed preservation001 audit SHA-256 is
`a42e0a13ea5b234ebcd2093a7db515ecc7578ff5348b1e8af533d2c142040d62`;
process closure is the parent attestation, not an independent PID survey.
Successful preservation002 review hashes all 28 private files and checks both
reads, separate verification and raw factory frames; six saved process groups
are absent. Query group IDs and live Docker absence were not independently
checked. Review SHA-256:
`bbd32c3a999fc45ff36581f8a1804c6850592e1b37ce34a247761ca63a4107c6`.
