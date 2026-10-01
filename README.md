# ESP32 SDR Lab

An evidence-based evaluation of an original ESP32 as an experimental SDR, alongside an attached RTL-SDR Blog V4 and available FPGA options.

- [Research site](https://knewter.github.io/esp-sdr-stuff/)
- [Experiment board](https://knewter.github.io/esp-sdr-stuff/work/)
- [Primary sources](docs/research/source-index.md)
- [Chip identification](docs/evidence/board-identification/README.md)

The connected chip is ESP32-D0WD-V3 revision 3.1, with 4 MB physical flash. Its observed firmware is an ESP-IDF hello_world/pin-toggle program, not an AtomVM startup. ESPARGOS ESP-SDR supports original ESP32 chips, but reception on this board remains untested. No firmware was written during this inventory.

Seven OpenSpec proposals cover firmware preservation, snapshot capture, RF characterization, short-burst applications, FPGA feasibility, AtomVM integration and receiver comparison. All hardware tasks remain unchecked. Design diagrams are labeled mockups; boot/probe logs are measured evidence. Adiuvo Forgix and a PCIe FPGA candidate have separate feasibility gates.

## Development

Use Node 22+, Python 3.12+ and OpenSpec CLI 1.11.0. Run:

```sh
npm ci --prefix site
openspec validate --all --strict --no-interactive
python3 -m unittest discover -s tests -p 'test_render_specs.py'
python3 -m unittest discover -s tests -p 'test_work_board.py'
python3 scripts/build_site.py --local
python3 -m http.server 4321 --directory site/dist
```

Commit OpenSpec and evidence changes before building: the work board and immutable source export render the committed Git snapshot. The build checks internal links, declared requirement status and output budgets. For the Pages prefix, set `ASTRO_BASE=/esp-sdr-stuff/` and `SITE_ORIGIN=https://knewter.github.io`. The GitHub Actions workflow builds and publishes pushes to master.

Keep full flash backups under ignored `backups/`; never commit firmware images or device identifiers. The read-only inspection tool resets the selected board and records boot output; it does not flash it. Select the stable serial identity before running it.

## Workflow origin

The spec/evidence renderer, work dialogs and regression tests are adapted from the neighboring T-Display-K230 project. [Provenance](docs/evidence/workflow-origin/README.md) records the copied revision and adaptation. No K230 hardware evidence is reused as ESP32 evidence.
