# Independent RAM firmware artifact review

Root reviewed the producer author's successful build 004 on October 2, 2026,
without opening hardware. [Checks](checks.json) independently bind the actual
ELF, map, symbols, disassembly and build log to the private manifest, its nine
historical committed source hashes, compiled identity, compiler executable
hash and assembled SDK NAR hash. Current firmware/helper bytes match those
historical inputs. The merged Taskfile differs; this review deliberately uses
the artifact's original committed Taskfile in its source identity.

An independent ELF-header parse agrees with the author guard: two ordinary-SRAM
LOAD ranges, 35,948 allocated bytes, 4,096 reserved stack bytes and no core1
stack or heap. The ELF entry is `0x2000016d`; the vector reset handler is
`0x20000199`, rather than the entry. Linked entry code installs the vector table,
loads its initial SP and branches to that handler, consistent with the pinned
SDK no-flash startup. The initial SP is `0x20082000`. Profile, compiled source
identity, distinct USB product and RP2350 RAM IMAGE_DEF are in loaded bytes.

The linked `main` enables the two-second watchdog before direct TinyUSB
initialization. Failed USB initialization requests reboot and stops feeding.
The producer has one TinyUSB scheduling owner, a finite 60-second run, fixed
two-second drain and independent 120-second main lifetime. Selected application
GPIO, UART, SPI, PIO, allocation and flash-write symbols are absent; this is
selected linked/source inspection, not a proof about every possible instruction.

The linked SDK startup does reset and release ordinary IO banks/pads. It can
change pin states and is outside the application watchdog. The user now reports
USB-only attachment and can replug, supplying physical recovery availability;
neither statement establishes successful replacement-image recovery. Absence
of an FPGA programming command does not establish unchanged FPGA state across
MCU resets. FPGA grade/oscillator/revision remain unknown.

Thirteen firmware guard tests and 28 collector synthetic tests pass in the
integrated locked Nix environment. Collector/lifecycle review remains separate.
The [first physical protocol](../../research/forgix-usb-ram-trial-protocol.md)
requires full device flash verification before and after, exact identity binding
and confirmed process/handle closure. No physical RAM load, throughput,
enumeration or recovery result is claimed here; original hardware tasks remain
unchecked.
