# Working on the ESP32 SDR evaluation

Keep plans in OpenSpec and proof in `docs/evidence/`. Read
`openspec/config.yaml` and `.skills/sdr-spec-change/SKILL.md` before changing
requirements. Proposals describe evaluations; only accepted, verified behavior
belongs under `openspec/specs/`.

Confirm the ESP32's stable USB identity before using a port. The original
ESP32-D0WD-V3 rev. 3.1 is behind a CP2102 bridge; the dual-serial ACM device
belongs to a different project. One operator owns the ESP32 port at a time.
Close serial handles after each operation.

The active user goal authorizes experimental ESP32 flashing/restoration after
verified preservation, receiver tests, and documented reversible FPGA trials.
AtomVM integration is explicitly deferred. Complete preservation before any
experimental firmware trial. Keep full flash
backups in ignored `backups/`, outside Git and the site. Do not publish device
addresses, credentials or network names.

Local commits are the work board's source of truth. Commit scoped planning and
evidence checkpoints before building. Do not mix a committed work board with
dirty evidence/specs. Site screenshots prove the site, not reception. Label
design illustrations explicitly. Keep hardware tasks unchecked until their
named physical evidence is recorded. Do not archive unfinished experiments.

Use the locked Nix flake for dependencies and the Taskfile for repeated work.
Do not install project dependencies globally or through ambient pip/npm.
Validation: `nix develop --command task check`; production/CI check:
`nix develop .#ci --command task check:pages`. Browser checks own their preview
and wait for readiness before connecting. Hardware tasks still need an
identity-selected device and an exclusive operator; entering a shell grants
no device permissions and starts no hardware operations.
Use separate worktrees/path ownership for concurrent work; delegation is not
required for ordinary single-operator work.
