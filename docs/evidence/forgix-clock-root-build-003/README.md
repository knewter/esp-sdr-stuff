# Fresh clock observer build: software preparation

The root-owned FPGA compile and fresh ARM003 build pass their offline guards.
ARM003 embeds the complete 173,380-byte observer image, uses 206,132 bytes of
ordinary SRAM, and retains the checked UID, active CRC body and exact ten-word
input-only PIO program. No board was opened, RAM image loaded or FPGA programmed.

The FPGA image was compiled at `5b35749` for the **assumed** T8F49/I2 target,
with direct B4/Y2 clock input, no PLL and four assigned internal pins. All four
vendor stages pass. Independent saved-report review finds nominal internal
setup +13.280 ns and hold +0.642 ns. These figures do not measure the fitted
grade, oscillator, rails, pad timing or contention safety. All nine FPGA build
inputs remain byte-identical for ARM003; the original manifest is preserved.

ARM003 was built at `9e73a34` using the dedicated Nix/Task route. The two earlier
attempts remain failed: ARM001 discarded the inlined standalone CRC symbol;
ARM002 reached the PIO metadata guard and exposed its version mismatch. The
reviewed corrections retain one active CRC function and explicitly bind PIO
version 1. They preserve the instruction words and exact metadata checks.
[Retained failures and source reviews](../forgix-clock-observer-preparation/README.md)
include 62 final host groups, the actual pinned SDK native fixture, and three
independent PIO groups. Saved failing artifacts were diagnostic inputs; only
the separately rebuilt ARM003 passed its original build route.

The saved startup audit returns `recognized_reset_transition_requires_qualification`.
It checks recognized linked reset/table paths; it does not qualify the whole
boot path, factory pin ordering or stopped-clock electrical behavior.
Independent complete linked-code and recovery review remains a separate gate.

A fresh read-only runtime receipt at the same revision binds 88 committed
execution inputs, seven selected tools, 268 content-verified Nix paths and
1,097 reference edges. It also rechecks the local loaded picotool image against
its Nix archive. It starts no container and accesses no board. Runtime and
whole-artifact independent review remain pending in this checkpoint; hashes
and scoped terminal results are in [checks](checks.json). Private manifests,+execution inventories and environment receipts remain unpublished.

The 2026-10-05 01:06:50 UTC survey finds the preserved ESP32 and RTL-SDR,
but no matching Forgix in factory, ROM or RAM mode. No serial port was opened.
Measurement admission and all registries remain empty. Task3.2 and physical
tasks stay unchecked: actual board mapping/electrical assumptions, complete
review, preserved loading/recovery and relative clock measurement still precede
register/SPI qualification and several-rate FPGA transport measurements.
