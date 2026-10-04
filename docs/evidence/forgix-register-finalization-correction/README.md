# Register qualification and finalization correction

October 4, 2026: **corrected author checks pass; independent review pending**.
[Checks and exact hashes](checks.json) bind source `54bda122`, prospective
correction plan `279437b`, and the unchanged failed `69e22dff` freeze.
This supplements the [original source preparation](../forgix-register-host-runtime/README.md).

Independent review found three concrete defects behind the empty qualification
registry: original UID/flash baseline substitution retained the old registry
key, final lease release could exceed 600 seconds while CLI0 was returned, and
a release/fsync error could leave a completed session on disk. The original
failed receipt and exact probes remain immutable. Against corrected source,
those probes now refuse the substituted board and return CLI2 with a failed
saved session for both finalization failures.

Qualification now binds the original UID and flash baseline in its registry key
and receipt; contained workers recheck original preserved binding. Lifecycle
completion remains provisional through finalization. One acceptance clock
includes lease release, both terminal acknowledgements and pending-marker
closure. Errors retain the primary failure, correct saved outcome where
possible, and restore a conservative lease. An independent durable pending
marker blocks another operator if active-lease recreation fails. Failed
corrective journaling remains uncertain with pending evidence and blocker; a
standalone session status cannot admit another trial.

All 136 distinct locked host-only groups passed, including actual temporary
lease/release, final persistence/deadline errors, cancellation, failed corrective
journal, pending-marker closure and refusal of mutated/malformed UID/baseline.
Current 36 inputs, seven tools/archive bytes, all 268 Nix contents and 1,097
reference edges passed fresh read-only verification. A real harmless query
worker passed actual inherited-lock and original-binding logic using two
independent full 2 MiB fixture copies; the child fixture baseline/continuity and
registry declarations do not prove any real board.

The shared synthetic runtime, synthetic backend/coordinator and standalone USB
helper remain byte-identical. Its full source map is 65 and still requires a
fresh merged root production freeze. The historical register configuration003
artifact remains correctly refused by the strict build-source guard; fresh
root-owned ARM build and independent artifact review remain required. Loaded
Docker identity is historical only. No daemon query, hardware access, container,
ARM compiler, vendor build or physical/OpenSpec acceptance occurred.
