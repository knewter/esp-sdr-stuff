# October 4 independent-work checkpoint

The complete production check passes at `0be88235f2ec9a9218632524b91d8984b0ee589c`:
911 host tests, two skips, OpenSpec validation, production site/link/budget checks,
actual native crypto and browser checks. This includes the merged RP startup
audit and corrected caller-owned collector. The later saved-waveform precision
implementation passes all seven focused groups in the root worktree; its whole
independent replay is recorded separately. [Exact scope and receipts](checks.json)
keep those revisions distinct. Tests are host evidence, not physical transport.

Commands use the locked Nix environment and repeated Task entries:

```text
nix develop .#ci --command task check:pages
nix develop .#ci --command task ble:precision:test
```

The prior published revision `0711ca4d007805438c8a61cb1176078b02d672f4`
passes live browser checks and byte-for-byte comparison of every exported source:
966 files and 19,346,955 bytes. That receipt describes the prior deployment,
not an assertion that the newest changes are already live.

A fresh read-only sysfs survey verifies the ESP stable identity, original backup
hashes and one RTL-SDR. It finds no Forgix factory or ROM device. No serial port
was opened. The [FPGA route](../forgix-synthetic-stream-artifact/README.md) still
requires physical qualification, a matching attachment and complete reviewed
loading/recovery. No hardware task, accepted radio gate or FPGA proof changes.
Private identifiers, raw captures and failed private receipts remain excluded.
