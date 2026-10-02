# Forgix host toolchain setup

Checked 2026-10-02. The project now has an actual Nix-built host environment
for Forgix: Migen, LiteX, the Forgix platform/target, MicroPython `mpremote`,
Icarus Verilog, Verilator and Yosys. Efinity is a separate licensed input;
no vendor compiler, license or FPGA bitstream has been installed or verified.
These checks opened no hardware and replaced no MCU firmware.

## Reproduce the completed host checks

```sh
nix develop .#forgix --command task forgix:check
nix develop .#forgix --command task forgix:host-check
nix develop .#forgix --command python3 -m unittest discover -s tests -p test_forgix_toolchain.py
```

`forgix:check` runs real imports, independent counter RTL generation, and
`mpremote --help`/`litex_server --help`; its receipt distinguishes host readiness,
vendor CLI readiness, confirmed compile inputs and successful gateware output.
Use `task forgix:check -- --output FRESH_PATH.json` for a fresh receipt.
`forgix:host-check` also runs the pinned upstream host suite: **17 tests passed**.
The local guards have **4 passing tests**. The Nix FHS wrapper built and ran;
without a vendor installation it refused with exit 2 as intended. This proves
the wrapper's missing-input guard, not compatibility with an Efinity binary.

| Component | Exact input |
| --- | --- |
| Migen | Nixpkgs recipe `0.9.2-unstable-2025-10-03`, source `147f003fb7076ac4c7cf76a9a5ce152dc10e0ca6` |
| LiteX | [`8c01073afb71aa0a0709f02f8e24247589e8f5e4`](https://github.com/enjoy-digital/litex/tree/8c01073afb71aa0a0709f02f8e24247589e8f5e4) |
| LiteX Boards | [`10debf146d433ce8ac8aedcac84e97d252ff4d5b`](https://github.com/litex-hub/litex-boards/tree/10debf146d433ce8ac8aedcac84e97d252ff4d5b) |
| mpremote | [1.29.0](https://pypi.org/project/mpremote/1.29.0/) |
| Upstream Forgix host tests | [`e7c71b750ca61690a70bc79ebd6ff5fbc65cedad`](https://github.com/enjoy-digital/aduivo_forgix_test/tree/e7c71b750ca61690a70bc79ebd6ff5fbc65cedad) |

All fetched sources have fixed hashes in `nix/forgix-toolchain.nix`; Nixpkgs is
locked in `flake.lock`. Runtime distributions report Migen 0.9.2, LiteX/Boards
2026.8 and mpremote 1.29.0. The independent RTL SHA-256 is
`b945624a91c355a350e7395b8321c7ed090290aef385310bcd387ea9a2118043`.

## Missing vendor input

A metadata-only search inspected about 414,000 filenames across downloads,
system/user software locations, configuration and local-share directories,
and neighboring projects, excluding caches and private backups. It found no
Efinity compiler, installer or matching license candidate. No credential or
browser-account store was read; this does not establish whether an online
Efinix support account exists.

The [Efinix Support Center](https://www.efinixinc.com/support/) currently lists
Efinity **2026.1.132**. Register or log in there, open its Efinity page, request
the free license, and download the Linux full-release archive. Efinix provides
free full licenses and free maintenance renewals; credentials and license
contents belong outside the repository and Nix store.
[Official license terms/workflow](https://www.efinixinc.com/products-efinity.html).

The [March 2026 installation guide](https://www.efinixinc.com/docs/efinity-installation-v4.1.pdf)
supports Ubuntu 20.04+ and RHEL 8.8+, specifies 8 GB RAM for Trion T8 builds,
and installs Linux releases by unpacking the archive into a user directory.
Its CLI setup sources `bin/setup.sh`; `efx_run.py --help` is the first smoke
check. Our Nix FHS environment supplies runtime libraries but is not a
vendor-certified OS or a tested Efinity installation yet. Java-dependent IP
configuration and GUI operation are outside the current SPIBone build check.

After placing a legitimate installation outside the repository, set
`LITEX_ENV_EFINITY` to that directory and run:

```sh
nix develop .#forgix --command task forgix:check -- --require-vendor
```

A passing help check verifies the CLI only. The license is considered compile
verified only after a real gateware build produces a passive-SPI hex image.
The upstream Forgix example reports validation with Efinity 2025.1; 2026.1
compatibility must be checked rather than assumed.

## Physical constraints and compilation gate

The [pinned LiteX platform](https://github.com/litex-hub/litex-boards/blob/10debf146d433ce8ac8aedcac84e97d252ff4d5b/litex_boards/platforms/adiuvo_forgix.py)
assumes `T8F49C2`, 32 MHz, clock ball B4 and its published I/O layout.
The [manufacturer schematic](https://bitbucket.org/adiuvo-engineering/forgix_public/raw/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/Schematic/RP2350_FPGA_eensy.pdf)
instead labels `T8F49I2X` and does not establish the fitted oscillator frequency.
The connected board's grade, oscillator marking and revision remain unverified.
No upstream default is accepted as a measured board constraint.

`--plan` and `--build-dir` require `--device`, `--clock-hz`,
`--board-revision` and `--verified-parameters`. The software cannot verify the
user's declaration; board inspection must support those values and the
published pin layout before compilation or any loading trial. `--build-dir`
requires a fresh directory, a working vendor CLI, and execution inside
`forgix-efinity` using the exported absolute `FORGIX_PYTHON`. It builds only;
there is no programming command. It enables SPIBone and on-board LED control,
with external demo I/O and scope disabled.

Keep the preserved native RP2350 factory loader. Installing `mpremote` on the
host does not install MicroPython on the board. The upstream MicroPython
SPIBone example is a possible later, separately preserved MCU experiment.
Its host unit tests and register transactions do not establish sustained IQ
transport rate, overflow behavior, latency, RF sampling or SDR usefulness.
Those need named physical evidence under the existing FPGA evaluation plan.
