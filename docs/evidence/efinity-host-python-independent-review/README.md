# Independent host Python runtime review

PASS for `1f0e17b348dd109c257900b606f607ebe5deceb5`; [checks.json](checks.json) binds source and private proof. All 33 Nix/Task tests passed. An independent real pinned-interpreter test passed imports and both host CLI help subprocesses under synthetic vendor Python settings. Only the explicit host alias removes PYTHONHOME/PYTHONPATH after FHS setup; HOME, PATH and other settings remain. Ordinary vendor help and all physical compile gates are unchanged. Python's [official option documentation](https://docs.python.org/3/using/cmdline.html) confirms the additional `-E -s` host flags ignore Python environment settings and disable user-site imports.

The author's original actual FHS log independently reparses to three successful host/vendor help checks, with no physical declarations or licensed compilation. Setup reports a C++ library compatibility warning; vendor files remain preserved. CLI help success does not verify compilation, licensing or FPGA operation. No vendor command or hardware operation was performed by this reviewer.

Reproduce tests: `nix develop .#ci --command task forgix:efinity:test`. The independent host fixture uses `nix develop .#forgix --command task -t .scratch/efinity-review/Taskfile.yml host-alias`; its ignored source/result hashes are bound in the receipt.
