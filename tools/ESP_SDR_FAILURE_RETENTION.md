# UART failure-prefix retention

This is host-side failure handling, not reception evidence or a retry policy.
Existing historical failures remain unchanged; discarded historical bytes cannot
be reconstructed by this change.

`exact()` preserves bytes delivered by successful `port.read()` calls before an
empty read, transport exception or interruption. Empty reads remain
`TimeoutError` compatible. Transport exceptions use `PartialReadException`, an
`OSError` with the original exception as its cause; its public description does
not reproduce a device path or transport error string. Interruptions retain
their original exception type. If a read raises after internally consuming bytes
without returning them, those bytes are unknown, explicitly recorded as such.
No extra read is attempted after a failure, even if a later tail becomes ready.

`capture()` binds the failure to the requested command, its write/flush outcome,
command/header/failure monotonic brackets and the parsed DATA count, full-payload
expected CRC and expected byte size where available. The actual header and
consumed payload prefix stay on the exception for private retention. The prefix
CRC is named separately and never establishes validity against a complete-frame
CRC. A malformed or incomplete header is kept privately, with no claimed payload.
`read_until()` exceptions cannot reveal bytes consumed internally; that limitation
also remains explicit.

The owned BLE receiver closes its serial port before failure-prefix persistence.
The snapshot loop likewise closes on fatal capture failure. Both stop the run;
they issue neither SYNC nor another CAP after ambiguous failure. RELEASE is
skipped when reply framing is uncertain. The spectrum caller retains its earlier
magic and any delivered body or end-report tail together, closes, and then saves
the failed packet separately from its accepted stream. Complete invalid frames
keep their existing rejection and retention behavior. No failed fragment enters
the owned receiver's success CSV; snapshot CSVs may contain an explicit error
attempt without valid full-payload CRC fields.

Private directories use mode0700; new private prefix/header/metadata/raw files
use0600 and exclusive creation. Saved bytes are checked against their in-memory
buffer. Disk failures leave created prefixes in place and report unverified or
failed persistence; they do not provoke a hardware retry. The owned receiver and
snapshot caller preserve the original read exception if terminal public receipt
publication also fails. Closure errors are recorded without claiming closure
succeeded. Raw bytes and header text do not enter browser state or public JSON.

`measure_owned_ble.py` keeps `integrity_failures` scoped to complete CSV captures.
Its separate `terminal_capture_failures`, `terminal_failure` and `failed_capture`
fields must be inspected: zero complete-frame integrity failures does not mean
that a failed terminal read was valid, saved, or part of the success count.

Host validation uses the locked Nix CI shell and an owned private Taskfile:

```sh
nix develop .#ci --command task --taskfile .scratch/failure-retention-task.yml test
```

The focused suite checks partial/empty/late/exception/interruption reads, parsed
headers and timing, exact private bytes and permissions, no retry, failed disk
writes/publication/closure, snapshots, spectrum framing, and the existing complete
receiver/demo regressions. It opens no hardware. Physical trials still require
fresh frozen runtime bindings and the exclusive root operator.
