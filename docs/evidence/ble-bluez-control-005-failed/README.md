# Eight-bit manual control: failed short read, original restored

October 4, 2026. The predeclared **8-bit / BW20 / manual48 / LO2401 MHz**
condition failed during its third source ON interval. UART payload read stopped
at **31,995 of 32,760 bytes**, leaving 765 bytes missing. Cleanup interrupted the
monitor and source. This is a failed trial, not a completed three-pair control.

Independent audit verifies all **1,047 retained complete payloads**
(**34,299,720 bytes**) and independently replays the unchanged decoder:
zero owned or other CRC-valid packets, with nine rejected candidates. Those
results cover the saved prefix only; they do not imply absent emissions or
confirmed detection failure. No source emission denominator exists.

The first two accepted ON intervals reached 120.100 and 120.225 seconds. The
third reached only 89.153 seconds before cleanup. There is no accepted final
OFF tail or normal monitor completion, so no complete fixed-band/control
qualification. Requested settings and successful prior phases cannot repair
this outcome. The [sanitized receipt](checks.json) records the exact limits.

The failed read fragment was consumed inside the reader and discarded before
its exception reached the recorder. Its bytes, DATA-header CRC and exact failed
request/header timestamps were not saved; the traceback retains only length.
The manifest's zero integrity failures applies to saved complete rows and must
not be read as whole-episode integrity. This gap cannot be reconstructed from
other captures. Future failure-prefix retention needs its own implementation
and tests; old evidence remains unchanged.

All owned UART/process/container resources closed. Independent audit verifies
fresh pre-install and post-trial **4,194,304-byte** original-image hashes plus
expected reset boot. No new electrical power-cycle measurement is claimed.
The failed inputs and logs stay private. No checkbox, accepted requirement,
source denominator or original Trial B gate changes. Continue the separate
hardware-gain condition while retaining this failed precision step and its
fixed-order/restart/interference confounds.
