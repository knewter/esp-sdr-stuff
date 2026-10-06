# C3 burst session 002: pre-declared protocol

Declared 2026-10-06, after session 001 and before any session 002 data exists.

**Session 001 stopped before the source started.** Pair 1 lost a UART read
after about 100 of 600 windows (32748 of 32760 bytes arrived), with the host's
load average at about 96 from unrelated work. As declared, it skipped the
remaining pairs and did not retry. Its 15 counted source cycles ran with no
capture listening, so no detection result exists.

The CP2102N link has no flow control, so a host that drains USB late loses
bytes. Session 002 changes one thing: the capture tool's new opt-in
`--recover-faults 30`. A faulted window is lost, its fragment is kept
privately, and the tool resynchronizes with its nonce fence before the next
window. A capture with more than 30 faults still aborts. Lost windows carry no
detection result, so they cannot bias the ON/OFF comparison. They are
reported.

Everything else is the [session 001 protocol](c3-burst-001-protocol.md)
unchanged: receiver, settings, source, three pairs of 600 windows with the
source starting at 40 s for 15 cycles, the fixed detector and thresholds, the
confirmation rule and the report-only packet decode.

## Stop conditions

On a capture abort (more than 30 faults, or any other error), keep the
completed captures and skip the rest. No retry. The C3 keeps the ESP-SDR image.
