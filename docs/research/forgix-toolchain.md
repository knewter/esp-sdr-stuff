# Forgix host toolchain setup

Checked 2026-10-02. The project now has an actual Nix-built host environment
for Forgix: Migen, LiteX, the Forgix platform/target, MicroPython `mpremote`,
Icarus Verilog, Verilator and Yosys. Efinity is a separate licensed input;
Efinity 2026.1.132 is now installed in permanent ignored local storage and its
CLI works through Nix. A complete generic T8F81/C2 vendor example now compiles
and produces a fresh bitstream; the connected Forgix build remains unverified.
[Complete compiler evidence](../evidence/efinity-compile-smoke-002/README.md). [Actual installation evidence](../evidence/efinity-install-001/README.md).
These checks opened no hardware and replaced no MCU firmware.

## Open components and the complete FPGA build flow

Rechecked current primary sources on 2026-10-02 after the user's open-toolchain
question. The MCU firmware, loaders and LiteX infrastructure have open source.
Yosys also implements [`synth_efinix`](https://github.com/YosysHQ/yosys/blob/main/techlibs/efinix/synth_efinix.cc):
its output stages write EDIF or JSON netlists. This is synthesis support;
it does not itself place, route or generate a Trion configuration bitstream.
The [current nextpnr supported-family list](https://github.com/YosysHQ/nextpnr#nextpnr----a-portable-fpga-place-and-route-tool)
does not list Efinix. This check found no maintained complete open T8 flow;
it is not a claim that no experimental or future implementation can exist.

The [current LiteX Efinix backend](https://github.com/enjoy-digital/litex/blob/master/litex/build/efinix/efinity.py#L366-L374)
names vendor `efx_pnr` and `efx_pgm` stages, then
[invokes Efinity's `efx_run.py --flow compile`](https://github.com/enjoy-digital/litex/blob/master/litex/build/efinix/efinity.py#L440-L453).
The [Forgix example linked by its manufacturer](https://github.com/enjoy-digital/aduivo_forgix_test#requirements)
explicitly requires Efinity. Thus the documented path for building new T8
bitstreams still needs that component. An open programmer or RP2354 loader can
transfer an already built image without implementing the FPGA build stages.

Efinity is **free of charge**, including its full license and renewable
maintenance. It still requires the vendor's download/license workflow;
[the official instructions](https://www.efinixinc.com/products-efinity.html)
say to register or log in to the Support Center and request the free license.
A new machine needs a legitimate installation and the vendor license workflow,
without a software purchase. These source checks ran no builds and opened no hardware.

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

## Permanent local downloads and installation

Use the locked shell for each command. The bootstrap does not download files,
accept a license agreement, install USB rules or program either chip. It copies
completed inputs, retaining the original Downloads files. Storage is the
repository's ignored `.vendor/efinity/`, with private directories and receipts
(0700/0600). Software executables retain owner execution permission. Licensed
files and captured vendor output never enter Git, the site or the Nix store.

```sh
nix develop .#forgix --command task forgix:efinity:discover
nix develop .#forgix --command task forgix:efinity:discover -- --source-dir ~/Downloads
nix develop .#forgix --command task forgix:efinity:import -- --full /path/to/efinity-RELEASE.tar.bz2
nix develop .#forgix --command task forgix:efinity:install -- --version RELEASE
nix develop .#forgix --command task forgix:efinity:check
nix develop .#forgix --command task forgix:check -- --require-vendor
```

For example, a full `efinity-2026.1.132.tar.bz2` package imports with
`--full ~/Downloads/efinity-2026.1.132.tar.bz2` and installs with
`--version 2026.1.132`. Replace `RELEASE` with the exact numeric release
recorded in the package's `scripts/sw_version.txt`. Discovery checks only a bounded top-level directory;
it reports incomplete browser downloads without opening them. Import refuses
`.crdownload`/`.part` inputs. No completed input means a friendly incomplete
result; partial browser files are not treated as installers.

The [official Linux installation guide](https://www.efinixinc.com/docs/efinity-installation-v4.1.pdf)
uses tar.bz2 full releases and ZIP patches. The importer also stages other tar
compressions or ZIP full releases when their layout is valid. Extraction guards
reject traversal, special files, hardlinks, duplicate paths and escaping,
cyclic or missing symlinks. Internal relative symlinks are supported. Archive,
member count, expanded size and available-space limits apply. A failed private
extraction is retained as `.failed-*`; it never replaces the current selection.
Successful installs use fresh version directories and atomic `current.json`
selection. Repeating the same software hash/version reuses the installation;
conflicting version bytes or changed required CLI files refuse.

Stage supplementary inputs explicitly:

```sh
nix develop .#forgix --command task forgix:efinity:import -- --patch /path/to/efinity-RELEASE-patch.zip --tool /path/to/vendor-tool.zip
nix develop .#forgix --command task forgix:efinity:import -- --license /path/to/private-vendor-license
```

Patches and standalone tools are retained separately and never mistaken for a
full compiler or silently applied to a different release. Applying a patch
requires its release-specific vendor procedure; staging it alone changes no
installed compiler. If more than one full release is staged, install also
requires its explicit `--archive SOFTWARE_SHA256` selection.

The installation guide does not specify a universal license environment
variable or filename. If the supplied vendor instructions call for a license
inside the installation, pass that exact safe relative location with
`forgix:efinity:install -- --version RELEASE --license-relative LOCATION`.
The helper copies opaque license bytes there without reporting their content,
hash or identifier, and refuses executable-file conflicts. A license already
configured by the vendor outside the installation remains untouched. No
invented license-variable setting is used, and CLI help does not verify a
licensed compile.

After selection, `forgix:check` automatically supplies the local installation
to the existing Nix FHS wrapper; an explicit `LITEX_ENV_EFINITY` still takes
precedence. `forgix:check` accepts host checks, declarations and vendor help;
compilation through `--build-dir` must use the private runtime below.
`forgix:efinity:run -- COMMAND ARGUMENTS` runs an explicitly supplied
command in that selected wrapper and retains its output privately. For example,
`forgix:efinity:run -- @forgix-python tools/forgix_toolchain_check.py --build-dir ...`
uses the pinned host Python with `-E -s`, after the Nix `env` helper removes
vendor `PYTHONHOME`/`PYTHONPATH` for that command and its descendants. This
prevents vendor Python paths breaking Nix host CLI tools and disables user-site
imports. HOME, PATH and the remaining vendor environment stay unchanged.
The ordinary vendor CLI check retains its complete setup environment; the
full host check also verifies vendor Python help from the isolated host path. This command
still requires all the physical declarations below. No command here chooses or
programs a hardware device automatically. Captured setup/command output stays under `.vendor/efinity/logs`. The vendor
may also create user logs in `~/.efinity`; HOME remains unchanged, and those
files and their permissions are not verified until a legitimate CLI runs.
Timeout or cancellation closes the whole owned command group. An unverified
group closure blocks later storage changes pending inspection. Sanitized output gives the exit code and software
version/hash, never a license-compile claim. Re-run the hardware-free bootstrap
guards with `nix develop .#ci --command task forgix:efinity:test`.

## Offline compiler verification

CLI help alone does not verify synthesis or licensing for compilation. A
separate bounded software fixture can check the installed compiler without
assuming the connected Forgix's grade, oscillator or revision:

```sh
nix develop .#forgix --command task forgix:efinity:compile-smoke -- --private .scratch/efinity-compile-next
nix develop .#ci --command task forgix:efinity:compile-smoke:test
```

The first command performs real offline compilation; it does not program
hardware. Use a fresh ignored directory for each attempt. The helper pins the
staged full release 2026.1.132, reviewed runner and four shipped `pt_demo`
inputs. It copies only those inputs, omitting shipped output/cache files, and
runs the fixed `--flow compile --timeout 300` command in the selected Nix FHS
runtime. The owned process-group timeout is 330 seconds, with bounded cleanup
before interpreting results. The installation remains unchanged. Logs,
projects and bitstreams stay private, outside Git and the site; failures retain
their partial outputs and `result.json`.

This fixture targets **Trion T8F81/C2**, as a generic software example. Its PLL,
oscillator and I/O assignments make no claim about the connected Forgix.
The [official user guide, pp.19 and 30](https://www.efinixinc.com/docs/efinity-ug-v16.1.pdf)
documents the example target and distinguishes compilation from programming.
The helper requires actual ordered `map`, `interface`, `pnr` and `pgm` PASS
markers, matching completed-stage logs and a fresh nonempty `.hex` with its
size and SHA-256. Here `pgm` generates bitstream data; `--flow program` is never
used. The separately named optional `export_bitstream` operation converts
files to binary when requested; this unchanged shipped example requests none.
No simulation, Java IP generator or programmer is required for this fixture.

A passing receipt verifies that the actual compiler accepted this generic
fixture in the current environment. It does not verify a connected-board
image, transport, timing, programming or FPGA behavior. The existing Forgix
physical-parameter declarations and compilation guards remain required for
that separate path. The [actual corrected compile](../evidence/efinity-compile-smoke-002/README.md)
passes all four stages and generates a fresh hex; the
[initial skipped-interface failure](../evidence/efinity-compile-smoke-001/README.md)
remains retained. Nix supplies SQLite and D-Bus libraries required by Interface
Designer. Fifty-one focused tests pass, and independent review checks both
actual results and the unchanged guards.

## Vendor download and license workflow

Before the user reported new downloads, a metadata-only search inspected about 414,000 filenames across downloads,
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
vendor-certified OS. The actual 2026.1.132 CLI, full host/vendor runtime checks and generic T8F81/C2
compilation now pass. SQLite and D-Bus libraries are supplied by Nix for
Interface Designer; the original bundled libraries remain intact. Java-dependent IP
configuration and GUI operation are outside the current SPIBone build check.

For an existing external installation instead, set
`LITEX_ENV_EFINITY` to that directory and run:

```sh
nix develop .#forgix --command task forgix:check -- --require-vendor
```

A passing help check verifies the CLI only. A generic offline fixture can verify that the compiler accepts a full build
in the current environment. Connected Forgix gateware verification still
requires its separate declared-parameter build and passive-SPI hex image.
The upstream Forgix example reports validation with Efinity 2025.1; 2026.1
compatibility must be checked rather than assumed.

## Physical constraints and compilation gate

The [pinned LiteX platform](https://github.com/litex-hub/litex-boards/blob/10debf146d433ce8ac8aedcac84e97d252ff4d5b/litex_boards/platforms/adiuvo_forgix.py)
assumes `T8F49C2`, 32 MHz, clock ball B4 and its published I/O layout.
The [manufacturer schematic](https://bitbucket.org/adiuvo-engineering/forgix_public/raw/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/Schematic/RP2350_FPGA_eensy.pdf)
instead labels `T8F49I2X` and does not establish the fitted oscillator frequency.
The connected board's grade, oscillator marking and revision remain unverified.
No upstream default is accepted as a measured board constraint.

The user's underside photo shows an AP MEMORY package and NANO / FPGA HORIZONS
branding. The [official Forgix specifications](https://forgix.tech/) list
RP2354, Trion T8F49 and APS1604M QSPI PSRAM, and link the
[FPGA Horizons Forgix store](https://merch.fpgahorizons.com/products/forgix-board).
The visible memory package and branding are consistent with that board;
NANO is consistent with the manufacturing partner's branding. This is a photo
interpretation, not a fitted FPGA identification: the underside image does not
confirm the opposite-side FPGA grade, oscillator marking or board revision.
It provides no reason to substitute another FPGA family's toolchain.

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
