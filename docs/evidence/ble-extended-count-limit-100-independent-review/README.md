# Independent extended100 preflight

**PASS for the frozen prospective source-only diagnostic**, reviewed offline on
2026-10-02 against source revision `52f827c17b8c9e25d0c0e59205f637bf1d24ce88`.
This review does not report a new physical controller count or RF result.

The subsequent [actual-001 review](actual-001-review.md) records matching
`0x43/count100` source/monitor events and successful source cleanup, while
retaining the whole episode as failed because the monitor hit its host deadline.

The [prospective protocol](../../research/ble-extended-count-limit-100-protocol.md)
permits one owned-handle extended100 episode: 20-ms interval, five-second
Duration, one-second start delay, a 30-second monitor and absolute 60-second
active supervisor followed by bounded cleanup. The source guard admits only
the existing extended255 or this extended100 profile. The dedicated caller
requires typed actual status `0x43/count100`, source exit 0, matching source and
monitor records, and complete cleanup. Duration failures stay failures with
parent exit 2. No retry, receiver operation or controller-global change occurs.

Independent Nix/Task replay passed 33 source tests, 12 original counted-report
tests and 19 private caller tests. Additional checks refused 29 malformed
source/monitor variants, retained four legitimate duration-count failures,
and compared 42 legacy command variants byte for byte with the prior source.
The scoped enable and disable bytes match the declared profile. These are
synthetic verification results, not hardware evidence.

All 22 frozen inputs and both retained fixture hashes matched. All 12 imported
project modules are included in that freeze. Both Nix image archives,
configuration commands and executable hashes were independently checked;
current recursive NAR bindings matched 22 source and 72 monitor closure entries.
The source and monitor images are distinct and remain separately bound in the
[machine-readable receipt](preflight.json).

The new [legacy100 public summary](../ble-count-limit-100-001/README.md) also
matches its original private receipts and prior independent review: four saved
file hashes and 22 inputs checked against historical revision `3b33da9`,
including the old source hash. Its timeout/count-zero outcome remains failed.

The reviewer opened no hardware device or Docker container. Root must confirm
current exclusive ownership, controller identity/state and unchanged inputs
immediately before any source launch. Source and monitor observe the same
controller; independent air emissions remain unknown. Original 255-event RF,
three-response and Trial B gates are unchanged.
