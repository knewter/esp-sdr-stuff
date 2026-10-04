# Runtime and source-profile checkpoint

October 4, 2026. Production checks at `800720a` pass **974 Python tests,
two skips**, native crypto, OpenSpec validation, site build and browser checks.
The focused synthetic Task passes all51 groups (35 lifecycle,14 runtime and
two actual-worker factory-return regressions). [Checks and hashes](checks.json)
bind the retained results and independent reviews.

The [source-only result](../ble-primary-zero-data-source-001-review/README.md)
and its measured host/HCI timeline are independently audited and reproduced
byte-for-byte. It qualifies the zero-data controller profile: native23 and
monitor11 records agree on five ACK0 pairs and termination0x43/count100. This
is controller-completed events, not measured air emissions or new ESP reception.

The [runtime correction](../forgix-synthetic-host-runtime/README.md) now refuses
a missing transitive dependency. The [factory-return correction](../forgix-synthetic-factory-return/README.md)
uses the existing admitted RAM query label; original refusal is retained.
A fresh root freeze binds63 committed inputs, seven exact host tools and268
content-verified Nix paths with1,097 reference edges. Independent comparison
confirms the current source map and exact previously verified environment.
The unchanged ARM001 artifact uses220,200 SRAM bytes. No vendor or ARM build
was repeated, and no Forgix was opened, loaded or programmed. Daemon/kernel/udev/
filesystem and pre-Python launcher trust boundaries remain explicit.

The fresh locked read-only USB survey finds the identity-selected ESP and
one RTL-SDR, but no RP-vendor USB device at any PID. Original ESP backups pass
hash verification, and the shared unknown-resource marker is absent. Forgix
attachment, physical grade, measured clock, voltage and pin timing/ownership
still gate physical qualification. Both admission registries remain empty.
The next fixed three-pair receiver preparation remains subject to independent
review and a fresh root freeze; no physical RF task or accepted requirement
is changed by this checkpoint.

Proof commands: `nix develop .#ci --command task check:pages`,
`nix develop --command task forgix:synthetic:trial:test`, and the read-only
private production freeze invoking the current artifact/runtime APIs.
This receipt proves local checks. Exact final production export, desktop/mobile
visuals, deployment and live source bytes are verified separately after commit.
