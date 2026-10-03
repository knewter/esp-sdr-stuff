# Forgix recovery after physical replug

Recovery 001 ran October 2, 2026 local time (October 3 UTC), using execution
revision `3aa20b7a66336811efb17b85c87c42bd3e9011fd`. Initial factory
HELLO/STATUS returned valid CRCs, ready/idle and zero bytes written. Two fresh
2,097,152-byte reads matched each other and the original SHA-256
`72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4`.
Separate ROM verification passed. All six scoped picotool operations closed.

**Overall recovery failed:** after normal application reboot, the returned
factory query failed with `PermissionError`/errno 13 before serial open.
No returned HELLO/STATUS was obtained. No RAM load, flash write, FPGA
programming or throughput measurement ran. Raw identities and all command
receipts remain in ignored private storage. The [original failed trial](../forgix-usb-ram-trial-001/README.md)
is unchanged.

The apparent device-node permission timing race is addressed by waiting for
read/write access within the existing 15-second factory-query budget. Identity
is checked on every poll and source inputs are rechecked before launch. The
worker receives only the remaining budget; its errors are not retried. All
35 focused tests pass, including delayed permissions, persistent denial,
identity replacement and late-worker rejection. The diagnostic tty receives
the same access gate within its existing 20-second enumeration budget;
failure still invokes factory/flash verification. This is preparation, not
a successful recovery result.

Independent review of `e315d6bc7aa897e6524f763b152d0ddebdf9e0b1`
replayed all 35 tests and five additional deadline/mutation/no-retry probes.
It verified recovery 001's raw reply CRCs, fresh flash hashes and six closed
step attestations. The private review receipt SHA-256 is
`93a0f718bc8dcc75af2e10f9f0b723ee74eeda6bd18cc52ac23646988dc046e1`.
The reviewer did not inspect live processes; root separately verified exact
owned containers/groups and the returned-query process were absent.

Recovery 002 used that reviewed revision. **It also failed**, at initial
serial `os.open` with errno 5 (I/O error), before any factory reply or ROM
operation. The kernel subsequently reported USB descriptor/setup-address
errors (including -71), and the selected device disappeared. This establishes
a USB enumeration failure, not its cause. No RAM load, flash write or FPGA
operation ran. Root requested another physical replug, an alternate data
cable if available, and confirmation of whether the USB port changed.
Factory return and aggregate recovery remain unverified; no automatic payload
retry or new rate condition has run.

Independent saved-file review of recovery 002 verified its five retained files,
all 13 frozen source inputs, selected private identity and prior backup hashes.
Its receipt SHA-256 is
`f5c4b0358108ac94bb142820dc9c253178a82fda74836071bc0b53199d34fcf9`.
Both failed recovery sessions lack an aggregate closure flag; the review does
not invent one or claim independent live-process/kernel inspection. Root's
selected-port kernel snapshot is retained privately.

## Fresh connection and recovery 003

After another user-directed reconnect, the factory-only check at execution
revision `852c5cfa4a8a3868825f26f961e94d6d94f668a6` passed: the original
private USB identity remained at one enumeration for **60.000929 seconds**,
with **121** identity/access samples. Initial and final HELLO/STATUS replies
had valid CRCs and ready/idle fields. Both serial workers closed. That check
requested no ROM transition, RAM load, flash write or FPGA operation.

One subsequent controlled recovery 003 at the same revision **passed**:
two fresh 2,097,152-byte reads matched the original hash above, separate ROM
verification passed, and returned factory HELLO/STATUS again passed. All six
scoped picotool operations and owned workers closed. Its terminal status is
`recovered_and_verified`, with original flash/factory verified and zero flash
writes. Earlier failures remain failed; this does not establish their cause
or general reboot reliability. No USB payload measurement has run yet.
