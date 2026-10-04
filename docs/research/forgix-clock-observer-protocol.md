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


## Task3.2 complete-profile implementation boundary (prospective)

This section defines the independently achievable next software work. It is
not a loading qualification or evidence of physical oscillator frequency.
Reuse corrected observer_capture/observer_rp_io, checked uid.c, the original
config.c/config.h/protocol CRC and direct TinyUSB descriptor/config primitives.
Do not include the register dispatcher or stream engine. Keep old candidates,
PID4012/4013 profiles, ELF policies and committed registries unchanged.

The smallest profile is a new no_flash main/CMake target and distinct USB
PID4014/product. Enable the2s watchdog before checked UID initialization, fail
without USB identity or application GPIO on UID/USB error, and retain an
absolute120s boot lifetime. Heap0/core1inactive/stack4096 remain mandatory.
Accept one complete fixed128-byte OBSERVE request, with version/op/reserved
checks, full nonzero128bit nonce, exact32-byte build and observer-image hashes
and CRC32. Consume its intent before configuration or any application GPIO;
partial requests and invalid/repeated commands cannot cause GPIO work or retry.
The complete command must arrive before boot+30s. Configuration uses the exact
image and existing min(now+20s,boot+30s) deadline; failure never starts sampling.
After successful configuration, observer_capture uses min(now+2s,boot+120s),
with both sides of clock/cancellation callbacks checked. The input boundary
owns only GPIO3/PIO0 for sampling; CS1 gates the burst and SCK2 stays low.

Return one fixed512-byte little-endian versioned CRC-protected result. Freeze
exact offsets before code: echo full nonce/build/image, configuration status,
observer status/count/all16 raw decrements, boot/configuration/capture/result
encoding timestamps and checked cleanup status; all unused bytes are zero.
No independent streaming, START retry, register read/write or frequency label
is added. One pending output buffer advances monotonically through actual CDC
accepted bytes, with no reset/resend/resynchronization. Bound USB drain to
min(result encoding+2s,boot+120s), then normal watchdog reboot. Complete host
reception/CRC is distinct from device enqueue; partial prefixes remain failed.
Retained samples on cancellation/timeout are diagnostic only. Ratio reduction
stays host-side exact rational and returns uncalibrated FPGA/PIO ratio bounds.

A new Efinity generator must directly bind sys to B4/Y2 (no PLL), reset safely,
map CS=G3/SCK=F3/F2 only gated observation output, and export the existing
production1024-period/divide1024 geometry with exact passive-x1 T8F49 candidate
assumptions. New image guard checks committed complete generated HDL/interface/
project/SDC hashes, four physical pins/OE path, source model and all actual vendor
stages plus fresh image. The current synthetic image guard specifically admits
its source/profile/map and must not be weakened or reused with an observer flag.
T8F49/I2/32MHz remain declared design assumptions, not fitted-part measurements.
Root alone compiles FPGA/ARM after separate source review. Preserve any failed
first artifacts. The generated exact-image C and build identity bind all source,
image, SDK/TinyUSB/compiler/pioasm and configuration bytes before/after build.

A separate ELF/startup policy must require the loadable observer marker and
checked UID/config/PIO/main symbols, exact linked10-word input program and image
hash/length/CRC, ordinary SRAM LOAD destinations/vector/metadata, no heap/core1/
flash/OTP/UART/SPI peripheral writers, bounded reply/object sizes and4KiB stack.
Use the separate256KiB configuration-image budget only in this new policy;
old128KiB policies stay exact. Audit SDK resets/constructors and selected main,
USB UID/configuration/input/cleanup/reboot call paths against exact linked code.
No whole-boot or pad-state qualification follows merely from a layout guard.

The private host collector uses the reviewed no-input-flush opener and
bytewise POSIX prefix retention. Send one durable request intent/one bounded
write only, preserve ambiguous write/read/late/cancelled prefixes, validate UID,
nonce/build/image/status/count/CRC/timestamps and full16-sample ratio coherence.
Do not auto-OPEN/retry/resync; checked closure precedes ROM recovery. A separate
owned process must bound serial calls; blocking library calls are not bounded
by Python check functions alone.

The distinct lifecycle retains exact original UID/two2MiB baselines, full fresh
pre/post preservation/verification/factory return and one600s acceptance clock
through final receipts, last inherited-lock close and lease release. Reserve
recovery time before loading. Initial preservation can mutate state. Reuse
bounded OwnedPicotool/targeted bus-address load and shared worker ownership,
marker refusals/global flock/durable cross-route lease, without broadening the
old application whitelist. Unknown closure prohibits new access. Known-closed
failed outcomes retain guarded recovery only; partial configuration/sampling
must still recover original flash and factory. Volatile prior FPGA state is not
restored by MCU flash verification.

Keep a separate initially empty measurement registry. Admission binds original
UID/baseline, complete execution/Nix/tool/image/ELF tuple, reviewed observer
contract, board assumptions and preserved loading/recovery/pin ownership.
It cannot borrow register/stream clock_verified qualification or seed physical
acceptance from host tests. A bounded measurement may test a nominal clock
assumption without declaring the original measured-clock/inventory gate passed.
Actual reset-to-factory pin ordering and input ownership must be reviewed first:
configuration resets FPGA before DATA output; observer cleanup inhibits CS
before freeing input PIO; factory HELLO/STATUS alone does not call config_begin.
Unexpected reset/stopped FPGA clock remains a hardware admission concern; no
subsequent factory programming transaction or DATA drive is authorized.

Host proof includes actual compiled-C UID/command/main/CDC partial/failure/
watchdog tests, actual async/generated HDL and PIO instruction tests, build/image/
ELF negative fixtures, real process/PTY inherited-lock/prefix/deadline/cancellation/
lease-death/recovery/persistence fault tests and immutable independent review.
New root-owned FPGA/ARM compilation and actual linked audits then precede any
separately reviewed measurement episode. Fresh attachment, actual board mapping/
electrical assumptions, undersampling/pad margins and factory recovery evidence
remain external/physical dependencies. USB cannot verify rails or calibrate the
RP reference; no external wire is needed for the documented internal route.

### Full-profile terminal correction (prospective)

The first complete host profile is retained at `c026cee`. Independent actual
coordinator fixtures found that a failed `session.json` fsync could be reread as
successful by its outer finalizer, and terminal stdout could cross the inclusive
600-second bound after a successful return decision. Preserve both failures.
The correction must propagate the primary persistence failure into an atomic
failed authoritative receipt; it must keep the shared pending marker across the
last operator-FD close, terminal output and remaining durable acceptance steps.
Output, storage, cancellation or deadline failure returns nonzero and cannot
promote saved bytes to success. The empty registry, wire contract, original
preservation, reset/pin qualification and all physical gates remain unchanged.
