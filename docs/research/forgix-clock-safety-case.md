# Reviewed clock safety case

The independent [documentary review](../evidence/forgix-clock-safety-case-preparation/README.md)
justifies all six review fields for one finite diagnostic on the preserved
USB-only intended board design. This private candidate grants no production
admission or physical acceptance. The [observer protocol](forgix-clock-observer-protocol.md)
and [actual artifact review](../evidence/forgix-clock-root-build-003/README.md) remain binding.

| Review field | Independent basis |
| --- | --- |
| `fpga_identity_assumptions_reviewed` | Preserved provenance; intended F49 C2/I2 speed 2 and nominal 32 MHz assumptions |
| `pin_mapping_reviewed` | Pinned PCB joins Y2/B4 and RP1/2/3 to G3/F3/F2 |
| `electrical_safety_reviewed` | Intended shared 3.3 V IO/core 1.1 V; bounded onboard drive/input ownership |
| `reset_pin_ownership_reviewed` | RP input/null reset state, raw OE inhibit with stopped clock, factory START forbidden |
| `whole_loading_recovery_reviewed` | Exact ARM003/image; complete owned RAM-load/factory-return path and quarantine |
| `startup_uid_reviewed` | Original private UID/baseline and selected linked UID/watchdog/startup ordering |

Assumptions: ordinary populated USB-powered board, common 0–85°C grade range
with normal room operation, no external pin driver, altered supply, overclock or
low-power/debug intervention. RN2 has 10 kΩ DONE pull-up and CS/CRESET pull-downs;
R6 pulls oscillator enable down through 1 MΩ. Passive pull-downs do not guarantee
reset logic levels. Safety relies on controlled DATA ownership and active reset
before output, not an assumed passive reset. Factory identity checks use only
HELLO/STATUS; MCU flash restoration does not restore unknown FPGA state.

No more photos or calibrated rail/clock measurements are needed to finish this
documentary case. Actual grade, rails, pad/no-alias timing and frequency remain
unmeasured; nominal 32 MHz/150 MHz and the digital interval are not calibration.
The 16-sample observer can abort its 1024-period burst. No register, synthetic or
ESP transport qualification follows automatically.

Survey018 found no Forgix. Reconnect the preserved data-USB board; a matching
identity, exclusive operator, fresh complete preservation and reviewed current
execution/tool/import/NAR/archive/environment/artifact tuple must precede any
separate registry admission and first diagnostic. The historical runtime proof
is retained, not newly reverified here. Registries remain empty and physical
hardware tasks remain open. Internal observer/register tests need no ESP wires.
