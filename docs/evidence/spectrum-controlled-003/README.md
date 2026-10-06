# Controlled spectrum session 003: ch37 located twice, run cut by a UART fault

Recorded 2026-10-06 under the [pre-declared protocol](../../research/spectrum-controlled-003-protocol.md).
The original image was preserved before the session, and restored and verified
by full readback afterwards.

| Ch37 pair | Counted events | Owned packets ON / OFF | Median carrier | Offset from 2402 MHz |
| --- | ---: | --- | --- | --- |
| 1 | 5,100 | 9 / 0 | 2404.171 MHz | **+2.17 MHz** |
| 2 | 5,100 | 9 / 0 | 2403.736 MHz | **+1.74 MHz** |
| 3 | 5,100 | 0 / 0 (capture faulted after 87 windows, about 10 s of ON time) | — | — |

Decoded owned packets locate the source cleanly. No owned packet decoded in any
OFF window. Within one session, the receiver's tuning offset changed by about
**0.4 MHz between two retunes to the same LO**. Together with sessions 001–002
and the hit-rate runs, the ch37 carrier has landed between +1.7 and +2.4 MHz
above nominal.

The third capture failed on a short UART payload, retained privately, after
only 87 windows. Short UART reads now limit long and short captures alike on
this heavily loaded host. Under the pre-declared three-pair rule, **task 1.2
remains unconfirmed**: ch37 is 2 of 3, and ch38/39 did not run.

Summary: [results.json](results.json). Raw IQ stays under ignored `.scratch/`.
