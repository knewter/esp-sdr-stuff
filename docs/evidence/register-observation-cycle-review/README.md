# Compiled cycle-bracket review of candidate002

**Offline author review of actual machine code; no hardware execution or RF
result.** The source author inspected the fresh register-diagnostic ELF produced
from commit `bf96681a9382367bfb759ee658d42392c4b1b9fe`. This supplements the
separate independent artifact and lifecycle review; it is not an installation
approval. Candidate001 remains retained and unapproved.

The compiled bracket covers the complete non-inlined observation-body call at
all five stage locations. It includes body entry/return, eligibility and
capacity checks, pointer calculation, both timestamp calls, the single RX_GAIN
read, original record-field stores and the record-counter update. Compiler
barriers kept that work between the counter reads. The compiler inlined the
wrapper; this artifact has no separate wrapper prologue or return.

[checks.json](checks.json) pins the actual ELF, application, generated
configuration, map and public disassembly excerpt.
[instructions.txt](instructions.txt) contains only the relevant compiled code.
The entire disassembly stays private, with its hash retained. Nix supplied the
Xtensa objdump; a private Task recipe ran the bounded dump and extraction.
No serial, USB, HCI, Docker or RF operation was performed.

| Stage | Opening CCOUNT | Body call | Closing CCOUNT | Residual after closing read |
| --- | --- | --- | --- | --- |
| post_settings | `0x400dc587` | `0x400dc58f` | `0x400dc592` | `beqz`, opening-counter stack reload, `sub`, final `s32i` |
| before_acquire | `0x400dbe05` | `0x400dbe0a` | `0x400dbe0d` | `beqz`, `sub`, final `s32i` |
| armed_before_trigger | `0x400dbecc` | `0x400dbed1` | `0x400dbed4` | `beqz`, `sub`, final `s32i` |
| dump_complete | `0x400dbf64` | `0x400dbf69` | `0x400dbf6c` | `beqz`, `sub`, final `s32i` |
| restored_after_dump | `0x400dbfc0` | `0x400dbfc5` | `0x400dbfc8` | `beqz`, `sub`, final `s32i` |

The body occupies `0x400dbb18..0x400dbba3` (end exclusive). Its two
`esp_timer_get_time` calls are at `0x400dbb55` and `0x400dbb66`; the RX_GAIN load
is at `0x400dbb60`, between them. All original field/counter stores finish by
`0x400dbb9c`, before `retw.n` at `0x400dbba1`. The counter difference is stored
at record offset 24 after the closing read. Actual linked records occupy 2,592
bytes: 81 records of exactly 32 bytes. The two serialization buffers remain
2,048 bytes each, separate from the MAC sample slab and its instruction alias.

One stage-argument `movi.n` lies inside each acquisition bracket. The initial
bracket also includes a stack spill of its opening counter. These are included
in the raw measured interval, rather than subtracted as an assumed zero-cost
setup. The two counter-read instructions and the post-boundary instructions
above remain measurement work. We enumerate instructions, not calibrated
instruction latencies. Function/register-window, memory and interrupt latency
cannot be recovered from instruction counts alone.

The full linear objdump stepped into unreachable alignment bytes before the
capacity-check branch target. That block was decoded again starting exactly
at `0x400dbb34`; the public excerpt replaces the misleading linear decoding
and omits the unreachable alignment bytes. The separate block hash and exact
addresses are retained. Its real capacity load/compare precedes all timer/read
work inside the measured call.

The profile guards a nominal 240 MHz clock, one core and disabled dynamic power
management. Raw `hook_cycles` includes any interrupt or task preemption between
the snapshots. Dividing by 240 gives nominal microseconds only. Unsigned
subtraction handles an ordinary wrap; a pause spanning a whole 2^32-cycle
period, about 17.9 seconds at that frequency, is ambiguous. The existing
timestamp brackets and independent deadlines remain separate observations.
This review proves compiled coverage of the declared bracket, not exact total
instrumentation perturbation, calibrated RF timing or SDR reception.

The source remains based on
[ESP-SDR 550fade](https://github.com/ESPARGOS/esp-sdr/tree/550fadea4d00a9e26ce921c5832167becb3dc20c),
with [ESP-IDF 25fe69](https://github.com/espressif/esp-idf/tree/25fe69f946311abdaf9ad56591f25fedbc20ac98).
The pinned SDK's
[cycle-counter API](https://github.com/espressif/esp-idf/blob/25fe69f946311abdaf9ad56591f25fedbc20ac98/components/esp_hw_support/include/esp_cpu.h#L179-L194)
returns the current core's cycle count. The separate diagnostic adds read-only
observations and measurement instructions; the original RF writes and declared
hook placement remain unchanged.
