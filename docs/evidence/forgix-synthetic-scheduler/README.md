# Countdown scheduling preserves exact source behavior

October 4, 2026. The [third routed failure](../forgix-synthetic-compiler/README.md)
identified a 64-bit tick-minus-start path into finite completion. The source now
loads a period-minus-one countdown on START and every offered record. Zero marks
the exact due edge; FIFO overflow still advances offers and sequence. Absolute
record timestamps, STOP, snapshots and drain remain unchanged.

[Checks](checks.json) bind 16 author actual-HDL groups and nine independent
production-period edge fixtures. Full scaled targets for all three profiles
match immutable pre-change HDL from Git cycle by cycle, including bus output,
CRC and every FIFO slot. Independent aligned production checkpoints verify
first/last due, low/full timestamp rollover, concurrent full-FIFO POP/drop and
reset. Due-adjacent STOP/POP/SNAPSHOT behavior also agrees. The production
clock remains 32 MHz.

Repeat: `nix develop .#ci --command task forgix:synthetic:source:test`.
Full-target runs use a scaled simulation clock; production probes explicitly
accelerate aligned checkpoints. Neither establishes physical frequency or
routed timing. Fresh actual compilation, platform/collector review and physical
qualification remain required. No FPGA was programmed or hardware task accepted.
