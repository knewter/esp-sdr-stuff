# ESP32 SDR Lab

An evidence-based evaluation of an original ESP32 as an experimental SDR, alongside an attached RTL-SDR Blog V4 and available FPGA options.

- [Research site](https://knewter.github.io/esp-sdr-stuff/)
- [Experiment board](https://knewter.github.io/esp-sdr-stuff/work/)
- [Primary sources](docs/research/source-index.md)
- [Chip identification](docs/evidence/board-identification/README.md)
- [Current results and remaining physical gates](docs/evidence/evaluation-checkpoint/README.md)
- [Measured recommendations](docs/research/measured-recommendations.md)
- [Accepted snapshot and display experiment](docs/evidence/snapshot-baseline/README.md)

The connected chip is ESP32-D0WD-V3 revision 3.1, with 4 MB physical flash.
Its original image is an ESP-IDF hello_world/pin-toggle program. Two complete
backup reads match; the final post-trial restoration also matches every byte
and boots after reset. The board currently runs its original GPIO firmware. Recovery now also has user-confirmed power cycling and a matching application boot, accepted in [independent review](docs/evidence/power-cycle-recovery-review/README.md).

The clean ESP-SDR UART921600 build passed all 600 full-size snapshot CRC/count
checks across three rates and two formats. A 512-bin browser spectrum session
completed 60 seconds with 7205 valid frames; its first 1024-bin attempt failed
CRC and remains visible. Independent review reproduced the data, and that
proposal is archived with two accepted requirements. Full I/Q transfers take
about 361–451 ms, giving only 0.045–0.281% nominal RF time coverage in the series.

Four evaluations remain active: the repeatable demo workflow, controlled RF,
burst reliability and FPGA feasibility. Recovery, snapshot transport and receiver comparison are accepted
and archived; AtomVM is deferred by user. Five owned BLE packets pass
protected-PDU CRC and exact marker verification. The user's current dipole
receives WXJC at 101.1 MHz with no-FEC RDS, independently replayed.
The user reports no external RF equipment, so shared-signal sensitivity is
explicitly deferred. RF calibration, independently counted emissions and FPGA
bring-up remain open. Design illustrations are labeled separately from captures.

## Development

Use the committed [Nix flake](flake.nix) and [Taskfile](Taskfile.yml) for
dependencies and repeated work:

```sh
nix develop --command task
nix develop --command task check
nix develop --command task site:preview
nix develop .#ci --command task check:pages
```

The flake pins the tools and Python packages. Site dependencies come from a
fixed-hash Nix package using `site/package-lock.json`; `task site:deps` makes
a writable copy for Astro's cache without downloading npm packages. OpenSpec
is packaged at 1.11.0. The browser check uses Chromium from the flake, waits
for its owned preview to become ready, and stops that preview afterward.

Commit OpenSpec and evidence before building: the work board and immutable
source export render committed Git history. `task check` runs validation,
site build, host tests and browser checks in order. `task check:pages` uses
the production URL prefix; GitHub Actions runs that same task in the smaller
`ci` shell and publishes pushes to master.

Run `nix develop --command task --list` for the capture, plotting and FPGA
budget tasks. Pass tool arguments after `--`. Firmware builds use the separate
`nix develop .#firmware --command task firmware:build -- ...` environment;
its immutable SDK provenance is recorded with the build.

The [repeatable ESP demo](docs/research/esp-sdr-demo.md) has `demo:esp` and
`demo:esp:restore` tasks. The new workflow's fresh physical proof remains open;
its browser and cleanup tests are host evidence.

The [Forgix toolchain setup](docs/research/forgix-toolchain.md) provides a
separate host shell and checks without opening hardware:

```sh
nix develop .#forgix --command task forgix:check
nix develop .#forgix --command task forgix:host-check
```

Hardware tasks require explicit device/settings arguments and exclusive device
ownership. A development shell does not grant USB or Bluetooth permissions.
The Forgix shell includes a built Efinity runtime wrapper. A separately
installed licensed Efinity compiler and physical FPGA pin/clock inventory
remain prerequisites for gateware compilation; the MCU preservation proof is separate.

Keep full flash backups under ignored `backups/`; never commit firmware images or device identifiers. The read-only inspection tool resets the selected board and records boot output; it does not flash it. Select the stable serial identity before running it.

## Workflow origin

The spec/evidence renderer, work dialogs and regression tests are adapted from the neighboring T-Display-K230 project. [Provenance](docs/evidence/workflow-origin/README.md) records the copied revision and adaptation. No K230 hardware evidence is reused as ESP32 evidence.
