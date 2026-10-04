# Merged synthetic lifecycle software checkpoint

October 4, 2026. Root production checks at `9d308d04eef08aee89e03fa89af6a6aa58b3ac41`
pass **953 Python tests, two skips**, native crypto, OpenSpec validation,
site build and owned browser checks. The two skips remain explicit. The
focused `forgix:synthetic:trial:test` task separately passes all 35 tests.

The [whole lifecycle proof](../forgix-synthetic-lifecycle/README.md) records
35 author and 18 independent offline groups, automatic recovery, explicit
known-closed recovery and the actual POSIX prefix-loss correction. Earlier
failed and historical proofs remain separate. No physical task is accepted.

A fresh read-only root freeze verifies all **62 committed execution inputs**,
the existing complete ARM001 artifact and embedded FPGA image, current
firmware/guard matches, loaded immutable picotool image, SDK NAR and runtime
closure contents. SRAM allocation remains **220,200 bytes**. No vendor or ARM
compiler was rerun. The private tuple and its digests are retained; this is
software verification, not a physical qualification receipt. Both admission
registries remain empty. Any later executable-input change needs a new freeze.

The first freeze preparation timed out after 60 seconds evaluating a read-only
ambient Nix bootstrap expression. It remains failed. The second uses the
previously independently reviewed locked Nix executable, verifies matching
current flake/lock bytes and freshly verifies that package's contents before
runtime checks. It passes without loading containers or opening hardware.

The latest saved read-only survey verifies the original ESP identity/backups
and one RTL-SDR, with **no RP-vendor USB device at any PID** and no unknown
Forgix resource marker. Factory/ROM communication and FPGA loading therefore
remain unavailable. Physical grade, measured clock, voltages, SPI timing/pin
ownership, bounded loading/recovery and several-rate sequence/CRC transport
proof still gate the FPGA route. No FPGA was programmed, no source was run,
and no RF evidence or accepted requirement changed at this checkpoint.

Proof commands: `nix develop .#ci --command task check:pages` and
`nix develop .#ci --command task forgix:synthetic:trial:test`. The fresh private
freeze invokes the current production `freeze`, artifact and immutable runtime
validation APIs read-only; [checks](checks.json) bind the sanitized results.

This record does not assert publication of this new revision. Live publication
is verified separately after committing and deploying the work snapshot.
