---
name: sdr-spec-change
description: Plan ESP32 SDR experiments with evidence-aware OpenSpec changes.
license: MIT
---

# Planning an SDR evaluation

Change IDs describe an outcome. Every proposal includes why, impact, non-goals,
board requirements, dependencies and a measurable decision gate. Write the
proposal, delta specs, design and unchecked implementation tasks.

Capability groups: `board`, `radio`, `transport`, `runtime`, `docs`.
Keep observations, upstream reports, calculations and hypotheses distinct.
Requirements need a `*Grounding: ...*` committed evidence citation or
`<!-- UNVERIFIED: reason -->`. S3 demonstrations do not prove LX6 capability.

Each task group ends with its narrow proof command or concrete experiment and
expected record. Hardware tasks require physical proof. Site screenshots are
host evidence; signal-path drawings are design illustrations. Record dates,
commands, source revisions, settings, capture gaps and measurement limitations.

Preserve the whole 4 MiB flash before installing SDR firmware. Keep the dump
outside Git/site and record its size/hash only. Verify restoration from a fresh
boot. FPGA proposals start with board inventory, clocks, voltage and throughput
calculations. Never assume LX6 has S3 dedicated GPIO or SIMD instructions.
A measured negative feasibility result is useful.

Archive only when every task and evidence gate passes. Commit scoped evidence
and validate before building the committed work snapshot.
