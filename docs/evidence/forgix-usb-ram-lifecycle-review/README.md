# Independent offline RAM USB lifecycle review

October 2, 2026: **the frozen lifecycle review passes**, with no remaining
blocking code finding in author revision
`05673562a3670a03719f042c8bb8e45683260523`, following
`9328d9f8fd80e2887cb017c123d3af1afb41e38e`. A separate reviewer replayed
25 lifecycle tests through locked Nix/Task and ran the independent probes
retained here. The [receipt](receipt.json) binds reviewed source bytes and
numeric outcomes. No device, serial, libusb or Docker operation occurred.

The reviewed path binds the preserved factory identity to each selected USB
mode, derives a fresh unique tty through exact USB ancestry before each factory
query, and binds the transient diagnostic to its compiled hash and per-run
nonce. RAM loading admits only the exact historical ELF after its actual layout
guard and export/source hashes pass; bus/address selection is fresh immediately
before the scoped operation. The original preservation command whitelist remains
unchanged, with no flash, OTP or FPGA programming command added.

The collector remains subject to its absolute 85-second bound, with an owned
100-second outer worker limit. Factory queries use owned 15-second workers;
the lifecycle rejects acceptance beyond its 600-second session budget. Cleanup
confirms the whole process group and uniquely named container before recovery
access. Unknown closure survives marker, step and outer preservation receipt
failures, persists in the aggregate result, and blocks another run or recovery.
Marker and frozen execution inputs are rechecked after acquiring the shared
operator lock. Prior generic capture failure cannot mask later unknown recovery
closure. Fresh full flash reads, independent device verification and returned
factory HELLO/STATUS are required before loading and after every load-attempt
outcome.

| Independent probe | Observed result |
| --- | --- |
| Prior unknown closure at recovery entry | Exit 2; zero device-verification calls |
| Unknown or generic group-cleanup error plus failed marker write | Authoritative unknown-closure exception retained |
| Marker published at lock acquisition | Exit 2; zero hardware-session calls |
| Frozen execution input changed at lock acquisition | Exit 2; zero hardware-session calls |
| Exact historical build 004 artifact | Accepted; 35,948 allocated bytes, 4,096-byte stack, zero heap section |
| PT_LOAD physical destination changed to flash/XIP in memory | Rejected by the actual ELF guard |

Early review found missing persisted recovery admission and cleanup exceptions
that could be masked by failed receipt writes. The author corrected the pre-load,
collector and recovery paths. Root's later review found a marker race during
offline preflight; the final revision rechecks admission under the lock. These
resolved findings are covered by the replayed tests and probes. Reviewer fixtures
also required explicit Task working-directory handling and selection of an actual
PT_LOAD header for the mutation test before the final passing replay.

Replay with absolute paths to the reviewed source checkout and private build 004
directory:

```sh
nix develop --command task \
  -t docs/evidence/forgix-usb-ram-lifecycle-review/Taskfile.yml review \
  SOURCE_ROOT=/absolute/reviewed/source \
  ARTIFACT_DIR=/absolute/private/build004
```

The source checker rejects changes to the reviewed lifecycle and relevant
helpers. The probes use synthetic subprocesses, temporary files and mocked
entry points; the artifact probe reads local exports and mutates only a memory
copy. The operator still owns live identity/image preflight and any physical
trial. This review proves no watchdog reboot, unchanged device flash, factory
return, USB throughput, FPGA transport or RF behavior. Hardware tasks and
accepted specifications remain unchanged.
