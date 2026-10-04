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
actual SDK adapter body with explicit hardware stubs. The initial independent review then found clock-callback cancellation could
leave success and malformed callbacks could leave a stale successful output.
That failure receipt and original source/readiness remain retained. Prospective
correction `a7276a4` preceded source `77127ed`;17 author groups and7 independent
groups pass without skips. Final timestamp cancellation now refuses, primary
errors survive later cancellation, and refused outputs clear prior success.
Those stubs do not prove ARM linking, pad behavior or physical timing.

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

The final independent receipt is bound in checks. Future integration must bind
the module sys clock directly to B4/Y2 and inspect the generated clock report;
source-domain simulations alone do not measure the fitted oscillator.

Root merges the corrected core as `7064cb1` and the separate finite command
engine/wire as `e96d9fb`. The engine passes8 author and7 independent groups;
root `nix develop .#ci --command task forgix:clock:test` passes all25 groups
without skips. Software task3.1 closes. Task3.2 still requires complete builder,
collector/lifecycle and fresh root FPGA/ARM artifact/startup review; current
main/CMake tests are source and stub checks. Physical tasks remain unchecked.
