# Finite RP stream core passes independent actual-C review

October 4, 2026. The separately versioned engine owns configuration/START
intent, FPGA HEAD validation and matching POP/readback, sixteen immutable USB
frame slots, coherent final accounting and bounded cleanup. Source offers
continue while RP queue backpressure stops POP. CRC/tick/pattern failures and
ambiguous consumption terminate without retry. Accounted source loss remains
a failed zero-loss outcome.

[Checks](checks.json) bind 18 author and 11 independent actual native-C groups
with nonrecovering UBSan and no skips. Three failed peer review episodes are
retained. Corrections reject stale final snapshot validity, impossible
START/STOP/queue states, contradictory live flags and crossed deadlines before
side effects. The final implementation passes those exact retained probes.

Repeat: `nix develop .#ci --command task forgix:synthetic:stream:engine:test`.
The [protocol](../../../firmware/forgix-synthetic-stream/PROTOCOL.md) defines the
separate frame and lifetime contract. These injected transport results establish
engine behavior only. Platform adapter review, actual ARM build/startup/resource
audit, host collector, physical image/clock/pin qualification and complete
preserved load/recovery still precede hardware admission. No FPGA was programmed
and no physical task is checked off.
