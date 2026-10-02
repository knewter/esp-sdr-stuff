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

Three evaluations remain active: controlled RF, burst reliability and FPGA
feasibility. Recovery, snapshot transport and receiver comparison are accepted
and archived; AtomVM is deferred by user. Five owned BLE packets pass
protected-PDU CRC and exact marker verification. The user's current dipole
receives WXJC at 101.1 MHz with no-FEC RDS, independently replayed.
The user reports no external RF equipment, so shared-signal sensitivity is
explicitly deferred. RF calibration, independently counted emissions and FPGA
bring-up remain open. Design illustrations are labeled separately from captures.

## Development

Use Node 22+, Python 3.12+ and OpenSpec CLI 1.11.0. Run:

```sh
npm ci --prefix site
openspec validate --all --strict --no-interactive
python3 -m pip install -r tools/requirements-ble.txt -r tools/requirements-analysis.txt
python3 -m unittest discover -s tests -p 'test_render_specs.py'
python3 -m unittest discover -s tests -p 'test_work_board.py'
python3 scripts/build_site.py --local
python3 -m http.server 4321 --directory site/dist
```

Commit OpenSpec and evidence changes before building: the work board and immutable source export render the committed Git snapshot. The build checks internal links, declared requirement status and output budgets. For the Pages prefix, set `ASTRO_BASE=/esp-sdr-stuff/` and `SITE_ORIGIN=https://knewter.github.io`. The GitHub Actions workflow builds and publishes pushes to master.

Keep full flash backups under ignored `backups/`; never commit firmware images or device identifiers. The read-only inspection tool resets the selected board and records boot output; it does not flash it. Select the stable serial identity before running it.

## Workflow origin

The spec/evidence renderer, work dialogs and regression tests are adapted from the neighboring T-Display-K230 project. [Provenance](docs/evidence/workflow-origin/README.md) records the copied revision and adaptation. No K230 hardware evidence is reused as ESP32 evidence.
