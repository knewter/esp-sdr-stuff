# Forgix RAM USB trials and recovery

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
At that checkpoint, factory return and aggregate recovery remained unverified; no automatic payload
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
or general reboot reliability. No USB payload was measured in recovery 003.

## RAM condition 002: loaded, startup failed, recovery passed

At execution revision `dd58652e5c622abbbb14a441b0b894681a53c362`, one
65,536-byte/s condition loaded the independently reviewed historical build004
ELF and enumerated the distinct RAM diagnostic. The collector received **zero
bytes**, failing its CONFIG deadline after **20.039980584 seconds**. No START,
DATA, END or host pause occurred; throughput and loss remain unmeasured.
The finite image returned to factory. Both pre- and post-trial preservation
passed: fresh paired full 2 MiB reads, separate device verification and
CRC-valid factory HELLO/STATUS. The failed session records owned hardware
closure, original flash/factory verified, zero flash writes and no FPGA
programming. Earlier failures remain retained.

Private session receipt SHA-256:
`5d8904c4c23bcb1637ee8ced77d3d2003e9f689b4dfb48766c72b5f2840afe72`.
Capture manifest SHA-256:
`4efd26ae5a348dac9d728eeb44f6c3e3c466ff9c2d0fc17c5733598dbd8d9ec1`.

Locked pyserial 3.5 asserts DTR before an implicit input flush; pinned firmware
queues CONFIG once when TinyUSB sees DTR. This can discard the announcement,
but the empty capture does not prove the timing of this physical failure.
The collector now preserves input during open. A real local PTY regression
injects a valid CONFIG at DTR: stock pyserial loses it, the corrected opener
retains and decodes all 512 bytes. A second test verifies descriptor closure
on configuration failure. All 39 collector tests pass through Nix/Task.
This source correction is not a successful hardware result.

Independent review of condition 002 verified the loaded ELF, 13 frozen inputs,
four fresh matching flash copies, separate device verifications and ten raw
CRC-valid factory replies. It checked 14 recorded process-group closures and
independently found those groups absent; it did not query Docker containers.
Review receipt SHA-256:
`642e4d7a919aa90c5305d1614865f7b444efef37829823acbe98512c91df55c5`.
The committed opener correction at `6a9e6d29d0f437d3b22884cf757639b9fcfdacdc`
passed 39 independent tests plus six extra POSIX-open probes, including bytes
arriving at kernel open, unexpected-prefix rejection and descriptor cleanup.
Code/admission receipt SHA-256:
`14c9d69d97b9e0f7d0bf996dba395a535318507d2d8fc20b69e9faeb1d497070`.

## Condition 003: factory preflight stopped before loading

The separately declared attempt at that revision failed its initial factory
query: the USB DTR-control ioctl timed out (errno 110), and the parent's
15-second worker deadline expired. Total hardware session: **15.929222235
seconds**. The owned worker closed; no factory reply, ROM operation, RAM load,
capture, flash write or FPGA programming occurred. This does not test the
collector correction. Session receipt SHA-256:
`4c8eabe1fc9ec79433fa0d53a036b7e8821bd7f2c38a1a363262b5e79a5e4f51`.

A subsequent read-only sysfs survey still sees the original factory identity
and a read/write-accessible tty at the selected topology. Enumeration and
permissions do not prove factory communication. The condition 002 post-trial
flash/factory proof remains a historical pass; current factory communication
needs a physical reconnect and new verification before another declared trial.
No automatic retry ran. All FPGA tasks remain unchanged.

Independent saved-file review verified all five condition 003 files, frozen
inputs and original artifact. A same-user process scan found no matching owned
workers or unclosed marker; specific query PID reaping is a parent attestation
because no query group ID was recorded. Review receipt SHA-256:
`4fbf8ca3741ea745f107cd5d9c2936784353c69431880fc91c1e2f767d6370cc`.

## Condition 004: one MCU USB condition passed

After the next user reconnect, factory stability 002 passed for 60.000972
seconds with 121 identity/access samples. Recovery 004 then verified two fresh
full original 2 MiB copies, separate device verification and factory return.
Independent admission receipt SHA-256:
`d0fb0184ea5adff4902b19b99ca2f03e263ccc3da0ef2c8a45c24b0c693baa84`.

One RAM-only trial at `cc9599dcbcbccf7f4a926a08298616830b82908d` **passed**:

| Observed quantity | Result |
| --- | ---: |
| Requested DATA payload rate | 65,536 B/s |
| Device START to END | 60.000001 s |
| Host READY to END receipts | 59.972962819 s |
| DATA payload / records | 3,932,540 B / 8,549 |
| Host payload / receipt interval | 65,571.881 B/s |
| Framed host bytes / CRC-valid records | 4,408,832 B / 8,611 |
| Missing records / device discards | 0 / 0 |
| Actual host read pause / after READY | 0.101455235 s / 30.001229554 s |

All deterministic DATA payloads and nonce/profile bindings passed. END's
pre-enqueue counters report queue high-water 2 of 16, zero partial writes,
zero measured stall time and 4,408,320 CDC-accepted bytes (excluding END).
All 62 control snapshots report zero queued backlog before their enqueue.
Host DATA receipt gaps: p95 0.051371195 s, maximum 0.112110895 s; frames
from one read share a timestamp. The host read pause does not halt kernel USB
reception or establish a physical backpressure stress test.

Full pre- and post-trial original-flash verification and factory HELLO/STATUS
passed. Owned resources closed; zero flash writes or FPGA programming ran.
Session SHA-256:
`a1970545ad049de79e8bda49263e184773c37b25ffb098681c95949dbf64257c`.
Manifest SHA-256:
`e8bd3cb413d5e083014dce1848c29f7107a1d53c49dae8bda6ad215d8447ac29`.
Private raw SHA-256:
`fd1a62929acaa636260bf1351f84461be363357e9784f919b3b43f1240fa6870`.

This verifies one synthetic MCU-to-host USB condition, not maximum throughput,
FPGA transport, ESP DMA access or RF continuity. Earlier failures remain
failed; the collector race remains a possible cause of condition 002.
FPGA/RF task checkboxes remain unchanged. At this checkpoint no further rate condition had run.

Independent fixed-offset replay verified every CRC, deterministic payload,
sequence, profile, private nonce and control-counter reconciliation. Replayed
host receipt timing agrees with the table. Both device verifies, four fresh
flash copies and ten raw factory replies passed. All 14 recorded owned groups
were independently absent; Docker absence was not independently queried.
Review receipt SHA-256:
`ca4813947107b749d1179f1488d5e505ad3f0060809ceaa43828b9ccca38b85c`.

## Conditions 005/006: measured loss at 256 KiB/s

Condition005 failed at factory serial open, errno5, before any query write,
ROM/RAM operation or capture (8.067 s). Its worker closed. After the user's
reconnect, recovery005 independently verified two fresh full original-flash
copies, separate device verification and factory return. Failure-audit SHA:
`8df478490ffe0ff0de0a1b9e193c5710c4952b015df45cc563cc222dd3805ef9`.
Recovery-audit SHA:
`4bdfa525856db83d80a452444ccca7570ead804862c53bca73f66d8ebc678512`.

Separately declared condition006 at `213aff2` used the same reviewed RAM ELF
and an explicit 262,144 B/s START. **Zero-loss qualification failed**:

| Observed quantity | Result |
| --- | ---: |
| Device / host READY-to-END | 60.000002 / 60.001840703 s |
| DATA payload / records | 15,530,520 B / 33,762 |
| Host payload rate | 258,834.059 B/s |
| Framed host bytes / CRC-valid records | 17,317,888 B / 33,824 |
| Missing records / device discards / gap ranges | 431 / 431 / 13 |
| Queue high-water / partial writes / stalled time | 16/16 / 2,423 / 1.315917 s |
| Actual read pause / after READY | 0.100082557 / 30.023290385 s |

Independent fixed-offset replay verified every retained CRC, deterministic
payload, build/profile/nonce and counter reconciliation. All missing records
match device discards. 114 were observed before the pause; it cannot explain
all loss. Offline Nix/image/closure preparation ran concurrently on the host;
its effect is unmeasured. This is no USB throughput ceiling or FPGA/RF result.

Full pre/post preservation passed: four fresh 2 MiB copies, two device verifies
and ten raw factory CRC/idle replies. Fourteen retained groups were absent;
collector closure is supported by the verified cleanup path and same-user
worker scan, since its exact PGID was not retained. No unclosed marker remained;
Docker absence was not independently queried. No flash write or FPGA command.
The 64 KiB/s zero-loss result remains the qualified condition.

Session SHA:
`7da74f973127bf1c4bc4f7f812925db7d9610c211b1d4c1e97a899947324d950`.
Capture SHA:
`91c0834a376a42a951756dbdbb2b411ba9320d82e21a8a688eb343477dd5b6d3`.
Independent audit SHA:
`0c8779e9332221e3629d982f6eaa2215c11a55e230ae08c522f961a351c78370`.
Gap timing audit SHA:
`b0a155dca7a0725c261fbd488394d915670d0018ffeb29f4b85a46f198f1eff4`.
