# Forgix toolchain subagent follow-up

The pinned host toolchain is ready. This independent follow-up on 2026-10-02
actually ran the Forgix Nix/Task checks: imports and counter RTL generation,
CLI help, **17 upstream host tests** and **four local guard tests** passed.
Icarus Verilog 13.0, Verilator 5.052, Yosys 0.69+post and Task 3.53.1 ran.
No USB, serial, FPGA, MCU, Docker or programming operation was performed.

- [Fresh host receipt](host-receipt.json) is copied byte for byte from the
  independent check. Its result is `host_ready`.
- [Execution and source hashes](checks.json) identify the checked files,
  pinned Nix environment, real command results and remaining gates.
- [Fresh Nix build log](host-check.txt) records the 17 upstream tests. Those
  tests use host-side fake buses/pins; they do not prove physical SPIBone.
- [Existing setup instructions](../../research/forgix-toolchain.md) describe
  the guarded compile path and physical parameters that must be confirmed.

```sh
nix develop .#forgix --command task forgix:check
nix develop .#forgix --command task forgix:host-check
nix develop .#forgix --command python3 -m unittest discover -s tests -p test_forgix_toolchain.py
```

The actual FHS wrapper refused an absent `LITEX_ENV_EFINITY` with exit 2.
The checker also returned exit 2 for `--require-vendor` without an installation,
and for `--plan` without confirmed physical parameters. The absence tests
explicitly removed vendor environment variables. They establish the refusal
boundary; the default fresh receipt separately found no configured installation.
No new filesystem search or credential/license inspection was performed.

Efinix's [Support Center](https://www.efinixinc.com/support/) currently advertises
Efinity **2026.1.132** and directs users to register/login to request a free
license. Its [product page](https://www.efinixinc.com/products-efinity.html)
describes a full license and free maintenance renewals.
The [maintenance policy](https://www.efinixinc.com/support/sw-maintenance.php)
distinguishes the Trion/Titanium license term from annual upgrade entitlement
and says downloading/using the software is subject to its license agreement.
No account was created, agreement accepted, or authenticated session used.

No legitimate unauthenticated installer was established in this review. The
public software link leads to `support/efinity.php`; our direct anonymous GET
was blocked by the vendor firewall (HTTP 403). Browser-tool fetching also failed.
That access failure alone does **not** establish an authentication requirement
for every possible download route. The public license workflow still calls
for a support account. Firewall response identifiers and host addresses are
omitted from this evidence.

To finish the vendor setup:

1. Use an existing Efinix account, or register through the official Support
   Center. Request the free Efinity license and obtain the Linux full release
   through its Efinity page. Keep account and license details private.
2. Unpack the legitimate archive outside the repository and backups. The
   [March 2026 installation guide](https://www.efinixinc.com/docs/efinity-installation-v4.1.pdf)
   lists Ubuntu 20.04+ or RHEL 8.8+, 8 GB memory for Trion T8, extraction into a
   user directory, `bin/setup.sh`, and `efx_run.py --help` as CLI setup/help steps.
   The Nix FHS wrapper remains untested with an actual vendor binary; it is not
   vendor certification for this host OS.
3. Point the guarded check at that installation:

   ```sh
   export LITEX_ENV_EFINITY=/outside/repo/efinity-installation
   nix develop .#forgix --command task forgix:check -- --require-vendor
   ```

A passing vendor help check will establish CLI compatibility, not a working
compile license. Actual compilation also requires confirmed fitted FPGA grade,
oscillator frequency, board revision and compatible pin layout. Upstream
`T8F49C2`/32 MHz/B4 defaults are unverified; the published schematic's different
grade label remains a reason to check the physical board. The upstream example
was validated against Efinity 2025.1; 2026.1 compatibility has not been tested.
No gateware, physical transport, sustained IQ throughput or FPGA SDR capability
is claimed. The [preserved factory MCU](../forgix-preservation/README.md) remains
unchanged; installing host mpremote does not install MicroPython on the board.
