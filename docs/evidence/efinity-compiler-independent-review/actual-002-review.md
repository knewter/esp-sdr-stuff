# Independent actual compiler review: run 002

PASS. [Numeric proof](actual-002-checks.json) binds the original private receipts and fresh outputs from root source `d993a42`. An independent hardware-free replay checked the exact helper verifier and separately reparsed original console/stage completion records: map, interface, pnr and pgm each pass once, in order. The fresh interface LPF is present. The fresh hex is **520,140 bytes**, SHA-256 `0966d77c7aee2847354814d4e7d80292fc026b5cce237decbea5b81042ef0787`; its timestamp lies inside the 23.730891588-second run.

The installed original four project inputs and runner retain their pinned hashes. All 59 retained files are regular single-link files with mode 0600, under 0700 directories. The actual receipt verifies owned process-group closure; the unknown-closure marker is absent. Replay source, Task and FHS definitions match the executed source checkpoint. Raw vendor output, binaries, license information and host identifiers remain private.

This verifies the installed compiler/license context for the generic shipped **Trion T8F81/C2** example. It does not verify connected Forgix gateware, physical device grade, oscillator, revision, wiring or programming. Optional binary export was not requested. Run 001 remains failed with its missing interface/LPF/hex proof intact. No vendor command or hardware operation was executed by this reviewer.

Reproduce the ignored review with `nix develop .#ci --command task -t .scratch/efinity-review/Taskfile.yml compiler-actual`; the private script SHA-256 is recorded in the proof.
