# Locked Nix provider retention preparation

October 5, 2026. **Software preparation passes independent review. Actual
provisioning, full cost measurement and hardware qualification remain pending.**

The first root cost sample refused a missing selected Nix dependency. Its failed
outputs remain preserved, and separate administrative recovery has passed saved
review. The new dependency-only Task selects the exact Nix output from the
committed locked flake, realizes that output and retains registered indirect GC
roots outside temporary worktrees. It separately retains the existing bootstrap
and selected project/nixpkgs sources. It starts no measurement or producer.

Initial implementation001 failed independent source-derived review: it expected
bare root names where Nix prints `link -> target`, and expected a store target
where registration returns the root link. Corrected002 matches the pinned [Nix2.34.8 source](https://github.com/NixOS/nix/blob/2.34.8/src/nix/nix-store/nix-store.cc)
and [indirect-root implementation](https://github.com/NixOS/nix/blob/2.34.8/src/libstore/indirect-root-store.cc). All 29 author fixtures and four independent controls pass; the unchanged
three probes of the old defects now reject those outcomes. The reviewer froze
1,770 subjects, and the root rehashed that complete review before applying the
exact three-file implementation. The initial packaging failure is retained;
it incidentally copied existing store bytes while following fixture symlinks,
without executing Nix or mutating the store. Corrected packaging preserves links.

CLI selection, realization, metadata and registration are modeled in these
fixtures. Actual local symlink predicates, owned-client pidfd cancellation and
late-persistence refusal are exercised. This software review does not prove
registered production roots, fresh NAR contents, daemon cancellation or radio
readiness. An actual root operation and independent saved-evidence review must
precede a complete current source/import/tool/runtime rebind and one separately
declared read-only cost follow-up. Original 165/300 measurement bounds and all
radio clocks remain unchanged. OpenSpec task5.6 stays unchecked.

Use the [Taskfile](../../../Taskfile.yml),
[reviewed helper](../../../tools/source004_provider_retain.py) and
[fixtures](../../../tests/test_source004_provider_retain.py). The
[historical cost failure and recovery](../ble-primary-timed-source004-readonly-review/README.md)
remain separate evidence. Sanitized review facts are in [checks.json](checks.json).
