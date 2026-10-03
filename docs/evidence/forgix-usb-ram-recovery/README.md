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
