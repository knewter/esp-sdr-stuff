# Synthetic factory-return query correction

October 4, 2026: **PASS for the offline query-label correction** at
`cfa5fa2`. [Checks and source hashes](checks.json) bind 35 lifecycle, 14 runtime,
two factory-return and two independent groups.

The synthetic caller used `returned-after-stream`, which the shared query
worker refuses. Both loader branches reproduce that refusal with the original
source. The corrected caller uses the existing `returned-after-ram` label;
the shared helper and its whitelist remain unchanged.

The regression passes the actual caller label through the actual worker's
parsing and target/label admission. Harmless fixtures replace device, inherited
lock, signal and storage boundaries. Independent checks also cover both
recovery loader branches and refusal of a wrong product ID or USB topology
before any factory query. The unchanged helper is present with its exact hash
in the 63-input committed execution map.

This closes the separate source mismatch recorded in the
[runtime review](../forgix-synthetic-host-runtime/README.md). The qualification
registry remains empty. No serial or USB access, container, FPGA/vendor build
or ARM compiler ran. These checks establish offline preparation only; they do
not admit a physical stream trial or establish RF reception, throughput or
clock/pin timing. A fresh production freeze and physical qualification are
still required.

A separate read-only comparison binds the root’s fresh production freeze at
`cfa5fa2` to the same 63 committed inputs, seven tool byte identities, 268 Nix
paths and 1,097 reference edges. Its entire environment matches the previously
independently content-verified proof. The root Task additions contain both new
test commands. No NAR verification or image inspection was repeated during
this comparison; physical admission remains false.
