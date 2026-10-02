# Exact evidence image reuse passes independent review

The evidence site now serves images from its existing immutable source export,
avoiding eight duplicate image copies totaling 1,246,182 bytes. Original source
bytes, evidence pages, gallery, source links and RF acceptance criteria remain
unchanged. Standalone renderers without an export retain marked image copies.

The independent [receipt](checks.json) reviews author commit `09134f4`, integrated
through root commit `0265683`. Twenty-eight renderer tests, three site-output
tests and thirteen real browser groups pass. All 739 exported files match exact
Git blobs. The reviewed production build occupies 15,240,258 bytes; later
publication adds its own evidence and must pass the same production budget.

An earlier implementation could delete an arbitrary supplied asset directory.
It was rejected before integration. The correction establishes ownership before
cleanup: only the nonsymlink canonical generated subtree or a subtree with the
renderer's exact marker may be removed. Seven independent refusal/preservation
fixtures pass, including original source, backup, Git, agent, external and
symlinked directories. Two obsolete generated session-003 images were removed;
their originals survive. No physical operation was performed.

Repeated builds have identical output inventory and asset bytes. Whole HTML
varies with the preexisting displayed generation minute; the repeat comparison
normalizes only those two displayed timestamps, never source or image bytes.
Private replay scripts and log hashes are retained in the receipt.

```sh
nix develop .#ci --command python3 -m unittest discover -s tests -p test_render_specs.py
nix develop .#ci --command task check:pages
```
