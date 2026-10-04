# One-way clock observer preparation

Prospective software boundary, October 4, 2026. No loading CLI, build profile
or qualification entry is added. Original candidates, RAM artifacts, registries
and physical FPGA tasks remain unchanged.

Counter0x1000 needs safe SPI before readback can measure its clock. A distinct
observer instead uses the existing route Y2→FPGA B4→divider→F2→RP GPIO3(input).
RP19 only enables Y2; CS is G3/RP1, idle SCK F3/RP2. These are documented by
[the pinned Adiuvo schematic](https://bitbucket.org/adiuvo-engineering/forgix_public/raw/c1d83e3e6ad10fa1c5a927731b1e4f54e771bf0f/Schematic/RP2350_FPGA_eensy.pdf),
not electrically measured on this board. No external wires, LED, PSRAM,
Wishbone operation or SPI request belongs to this boundary.

FPGA reset/cold startup has OE0. Qualify 32 real synchronized CS-high/SCK-low
samples; long configuration CS-low and mode-3 SCK-high cannot arm. Once
qualified, CS-low consumes one burst: 1024 periods of divide-by-1024 followed
by a half-period low tail. Raw CS-high disables OE immediately. Abort or
completion permanently spends the burst until reset. No arbitrary sub-cycle
CS-glitch detection claim: the RP maintains stable controlled CS.

After separately verified exact-image configuration, RP holds CS high/SCK low,
GPIO3 input/pulls disabled, then an input-only PIO loop at integer divider1
counts 16 complete rising-to-rising periods. No output/set/side-set pin mapping.
The C capture budget is capped at two seconds; a caller cannot enlarge it.
FIFO blocking occurs outside each measured period: samples may skip whole
source periods and are not continuity measurements. One consumed attempt,
RP may stop with CS high after 16 samples, spending/aborting the FPGA burst
early. C status0 means completed sample capture and cleanup, not natural
completion or delivery of all1024 source periods.
fresh before/after callback deadlines, watchdog, retained completed samples and
CS-high cleanup apply on every failure. No automatic retry or register followup.

For the committed PIO instruction loop, each X decrement represents two
instructions. Transition/setup/sampling phases are conservatively enclosed by
`[2*n-16,2*n+16]` PIO clocks. An instruction interpreter checks the envelope
against asynchronous periods/phases. This digital bound excludes actual pad
propagation, metastability and unverified electrical synchronizer margins.
Physical interpretation also needs a no-undersampling envelope grounded in the
fitted FPGA/oscillator and actual RP clock configuration; digital samples alone
cannot exclude an arbitrarily fast aliased input.
Intersect each valid frequency-ratio interval `[1024/high,1024/low]`; refuse
zero/overflow/impossible/inconsistent measurements. No calibrated MHz or ppm
claim: RP's crystal/timer is not a calibrated standard. Clock ratio informs a
later SPI envelope but does not establish pad timing or contention safety.

Root must separately integrate a RAM profile: checked UID after watchdog,
one exact-image configuration intent by boot+30s, <=120s lifetime, 2s watchdog,
no flash/OTP writer/heap/core1, explicit SRAM/stack/startup audit and USB protocol.
An input-only RP without configuring this new FPGA image cannot measure Y2.

Before loading, independently review HDL/PIO/actual-C fault tests, then new
root-owned FPGA/RAM builds and exact four-pin placement/whole-code/startup audits.
A distinct measurement lifecycle requires original UID/full2MiB baseline,
exclusive inherited lock/durable cross-route lease, complete source/runtime/
artifact tuple, shared pending/unknown-closure refusals, fresh double full reads,
device verify and factory return before/after every possibly consumed mutation.
Initial preservation is mutating. Full MCU flash restoration does not restore
prior volatile FPGA state: audit factory/reset pin ordering, stopped clocks and
watchdog return while F2 drives. Unknown closure prohibits further commands.

Grade/revision/electrical/attachment gates remain. [Efinix's part table](https://www.efinixinc.com/shop/t8.php)
lists C2/I2 as speed grade2 with different temperature grades; it does not
identify the fitted part. [The datasheet](https://www.efinixinc.com/docs/trion8-ds-v5.5.pdf)
governs passive configuration/user-mode delays and supplies. USB cannot measure
actual FPGA rails. Manufacturer design assumptions need explicit diagnostic
review; no voltage or inventory task becomes verified by this software.

Original counter0x1000 readback remains a separately qualified cross-check.
Existing registries stay empty. No physical task or accepted requirement closes.

Independent-review correction plan (original4cd preserved): clock callbacks
can themselves raise cancellation, so admission must test it before and after
each clock observation, including the final result timestamp. A refused call
with a writable output must clear previous success fields before validating
callbacks. Actual compiled-C regressions will inject both final clock faults
and a stale completed result with a missing callback. This changes no physical
admission. The future generated clock report must bind this module's sys input
directly to B4/Y2; its unregistered caller-supplied sys domain alone proves no
board oscillator route.
