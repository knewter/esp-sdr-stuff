# One-way clock observer preparation

The [prospective protocol](../../research/forgix-clock-observer-protocol.md)
removes the first-read SPI clock dependency through a distinct FPGA divider on
existing F2 and an RP GPIO3 input-only period sampler. This is source preparation,
not a loadable profile, measured oscillator or admitted FPGA trial.

Planning `eaa253d` preceded source `4cd895432988eba5618a6ea069b61acbaeae115f`.
[Checks](checks.json) bind the immutable author receipt and subject hashes.
Fifteen locked Nix/Task groups passed in9.812s without skips; strict OpenSpec
validation passed. They execute asynchronous Migen/generated production Icarus
HDL, actual PIO assembly/literal instruction simulation, native C/UBSan and the
actual SDK adapter body with explicit hardware stubs. Independent review is
pending; those stubs do not prove ARM linking, pad behavior or physical timing.

The FPGA emits at most1024 divide-by-1024 periods, with cold-reset inhibition,
qualified idle, raw-CS output gating and a one-shot spent latch. The RP takes16
period samples, retains completed late/failed samples, remains input and checks
cleanup. It may end the burst early. Exact rational FPGA/PIO intervals reject
inconsistent/invalid counts; calibrated MHz, ppm accuracy and continuity are
not claimed. Input sampling/propagation margins still need qualification.

Existing candidates, RAM artifacts, registries and physical checkboxes are
unchanged. New RAM/main/USB/build/lifecycle integration, root-owned immutable
FPGA/ARM artifacts and independent whole-code/pin/startup review precede any
loading. Grade/revision/electrical/attachment and full preserved recovery gates
remain. No device, daemon, vendor compiler or ARM build ran here.
