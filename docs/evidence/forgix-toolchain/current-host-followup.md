# Bounded Forgix host follow-up

Checked 2026-10-02 at 09:10:54 UTC. The fresh
[current host receipt](current-host-check.json) is copied byte for byte; SHA-256
`fcbc081e7a2c09fc107cbca6a71200ab3daa1c78244d213eb5ecb8bd312e8b53`.
The [earlier receipt](host-receipt.json) remains unchanged.

```sh
nix develop .#forgix --command task forgix:check -- --output .scratch/forgix-current-host-check.json
```

This actual locked-Nix host check exited 0. Migen 0.9.2, LiteX/Boards 2026.8 and
mpremote 1.29.0 imported; independent counter RTL retained SHA-256
`b945624a91c355a350e7395b8321c7ed090290aef385310bcd387ea9a2118043`.
`mpremote --help` and `litex_server --help` passed. Available Nix commands include
`python3`, Task 3.53.1, `mpremote`, `litex_server`, `litex_term`, `litex_cli`,
Icarus Verilog 13.0, Verilator 5.052, Yosys 0.69+post and the
`forgix-efinity` FHS runtime wrapper. Installing host tools does not install
MicroPython or produce FPGA gateware. No hardware was opened or configured.

The follow-up inspected filename/stat metadata only, with maximum depth two
(home top level only) and 20,000-entry caps per root. Credential, browser-account
and license contents were not read. No Efinity installation/compiler/archive
candidate was found in the inspected entries; this bounded result is not an
exhaustive filesystem or online-account search.

| Location category | Entries checked | Search limit |
| --- | ---: | --- |
| Downloads | 20,000 | Entry cap reached |
| Alternate Downloads path | 0 | Same resolved directory; not scanned twice |
| System opt | 10,434 | Depth limited |
| System local | 78 | Depth limited |
| User local opt | 28 | Depth limited |
| Home top level | 438 | Depth zero |
| Neighboring projects | 20,000 | Entry cap reached |
| Total | 50,978 | Partial follow-up |

`LITEX_ENV_EFINITY`, `EFINITY_HOME` and `EFINITY_PATH` were unset. Vendor CLI
compatibility, compilation license and gateware output remain unverified. The
missing prerequisites remain a legitimate Linux Efinity installation and a
license that passes a real gateware compilation, plus physically verified FPGA
grade, oscillator frequency, board revision and matching pin layout. No board
constraint was inferred from upstream defaults. See the
[toolchain setup and vendor workflow](../../research/forgix-toolchain.md).
