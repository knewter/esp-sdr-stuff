## 1. Provide the repeatable workflow

- [x] 1.1 Implement and document Nix-backed `demo:esp` and standalone `demo:esp:restore` Task commands with verified identity, preservation and artifact gates; verify hardware-free help and meaningful preflight/lifecycle tests.
- [x] 1.2 Exercise the actual local viewer with Nix Chromium using synthetic frames; verify live canvas updates, start controls, gap labels and successful/failed terminal states without hardware access.

Proof command: `nix develop .#ci --command python3 -m unittest discover -s tests -p test_demo_esp_sdr.py`. The synthetic browser proof is labeled host evidence and does not complete the physical tasks.

## 2. Demonstrate the connected board

- [ ] 2.1 Run the documented Task command on the identified preserved ESP32 for 60 seconds; retain exact artifact hashes, settings, frame CRC/sequence/end totals, timing, gap flags and live/completed viewer evidence in a fresh physical receipt.
- [ ] 2.2 Verify the command returns the board to the preserved original image with a fresh independent 4,194,304-byte readback and matching original-application boot; retain restoration and failure/cancellation test outcomes separately from physical power cycling.

Physical proof command: `nix develop --command task demo:esp -- --artifact VERIFIED-ARTIFACT --manifest VERIFIED-MANIFEST --output docs/evidence/FRESH-DEMO --private .scratch/FRESH-DEMO --headless`. Actual paths and executed tool hashes are recorded in the private operator receipt; public evidence excludes personal/device identifiers and raw frames.

## 3. Review and publish

- [ ] 3.1 Independently replay the new physical spectrum and full-flash restoration checks, review lifecycle failure gates and rendered evidence, and publish the review without closing unrelated RF/burst/FPGA gates.
- [ ] 3.2 Commit reviewed evidence and workflow, validate OpenSpec and the production site through the Taskfile, push to GitHub, and verify the exact deployed revision, demo documentation and evidence links through GitHub Pages.

Proof command: `nix develop .#ci --command task check:pages`, followed by the exact-commit GitHub Actions build/deploy result and `task browser:live` with published source/evidence hashes checked against that commit.
