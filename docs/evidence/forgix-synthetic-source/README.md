# FPGA synthetic source: actual HDL reviewed, physical stream unverified

A separate finite source now produces **16-byte sequence/tick/pattern/CRC**
records into a **64-record FIFO**. Stable non-destructive HEAD reads and
matching-sequence POP keep multiword reads coherent. Full drops, refused POPs,
coherent counters, one-shot configuration and finite deadlines stay explicit.
The new Wishbone region at **0x00010000** preserves the old counter/scratch bank
at **0x1000/0x1004** and the existing guarded four-pin SPI boundary.

Independent review replays **34 tests** (11 source/wrapper, eight guard,
15 candidate) and adds **five actual-Verilog probes**. Tests cover all three
finite source sequences (960/3,840/7,680 records), independent zlib CRC,
stable HEAD, simultaneous POP/PUSH, full drops, stale POP, held requests,
cold reset, wrap arithmetic and coherent snapshots. A generated-top SPI probe
checks source configuration, records and POP through the real bus wrapper.
The [sanitized receipt](checks.json) binds the review and fresh root-generated
RTL. Root also runs the 11 source checks in the regular locked CI environment.

The nominal **256/1,024/2,048 B/s** presets are offered source-record rates,
not delivered USB throughput. Scaled HDL simulations preserve finite record
counts and relative bounds; they measure functional behavior, not hardware
bandwidth. The generator performs no vendor compile or programming. Resource
fit and timing closure remain unverified. No FPGA transport task is accepted.

The core's 100 ms POP-refusal fixture is a separate fault control. It does not
pause RP scheduling or the host reader, prove physical backpressure, or justify
blind retries of consumed requests. The original 24-command RP register bridge
cannot drain this source autonomously; separate RP and host stream code is
still required. Existing physical admission remains disabled.

See the [source and exact map](../../../firmware/forgix-synthetic-source/README.md),
[finite transport protocol](../../research/forgix-synthetic-transport-protocol.md)
and [configuration/recovery gates](../../research/forgix-spi-register-trial-protocol.md).
Repeated commands are `task forgix:synthetic:source:test` and
`task forgix:synthetic:source:rtl -- --output .scratch/<fresh-directory>` in
the locked Nix environment. Commit inputs before generation. The regular CI
shell now includes pinned Migen/LiteX/boards and Icarus; the dedicated `.#forgix`
shell retains vendor tooling. Private RTL/manifests are not hardware proof.

A matching attachment, actual board/clock/pin qualification, independently
reviewed linked RP images and complete preserved recovery still precede loading.
No ESP wiring is needed for the first internal synthetic benchmark; ESP SRAM
access and RF integration remain separately conditional and unverified.
