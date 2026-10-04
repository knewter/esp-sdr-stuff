# Preserve behavior while shortening the drain-control path

Offline review, October 4, 2026. [The failed actual build](../forgix-synthetic-compiler/README.md) misses requested 32 MHz setup by 0.694 ns. Its reported worst path runs from stop_tick through drain-deadline arithmetic, POP eligibility and FIFO high-water control.

The source now latches tick+five-second drain duration on the same STOP/natural-completion edge as stop_tick. The expiry comparison uses that deadline register, moving the wide addition out of the POP control cone. The clock constraint and SPI guard remain unchanged.

[Checks](checks.json) bind 14 source groups and 50 total author regression groups, including 19 cycle-by-cycle differential scenarios. Independent review reads original HDL bytes directly from Git and passes five groups with 22 actual HDL simulations. STOP/deadline edges, carry/wrap, concurrent full-FIFO final POP/STOP/SNAPSHOT, pause/reset, seeded traffic and production-parameter last-record tick/pattern/CRC agree. The initial oracle-construction test failure remains retained privately; its correction changes the test, not the source contract.

Repeat: `nix develop .#ci --command task forgix:synthetic:source:test`.
A fresh actual vendor build must demonstrate any routed timing improvement.
No physical clock, pin timing, programming or transport result follows.
