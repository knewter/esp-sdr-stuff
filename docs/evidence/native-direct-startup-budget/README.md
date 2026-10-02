# Move image loading outside the bounded native observation

Recorded 2026-10-02. These are **host checks**, with no ESP UART operation or
Bluetooth socket. They support a prospective startup optimization; they do
not prove that all six RF episodes will finish within the declared schedule.

The [failed first comparison](../native-direct-reference-001/README.md) took
8.579 seconds from source Task start to its first configuration record. Its
source wrapper loaded the Docker image inside that interval. Six five-second
episodes, five five-second OFF gaps and a ten-second baseline already require
65 seconds before startup/cleanup overhead. The unchanged source-closure
deadline is READY +75 seconds, with native stop at 90–92 seconds and final
OFF strictly greater than ten seconds.

| Actual host operation | Samples | Elapsed per operation |
| --- | ---: | --- |
| Load the pinned source archive into Docker | 3 | 1.167–1.217 s |
| Start its source `--help` container | 3 | 0.516–0.566 s |
| Inspect and verify an explicitly preloaded immutable ID | 6 | 0.015–0.069 s |

[Load receipts](image-loads.json), [help-container receipts](help-containers.json)
and [reuse receipts](image-reuse.json) retain every result. Help containers used
`--network none`, all capabilities dropped and a read-only filesystem; the help
path opens no HCI socket. Reuse calls exercised the actual committed wrapper
from `58a25b4`, verifying the selected ID each time without loading or starting
a container. All six metadata checks together took about **0.151 seconds**.
These small samples are not latency guarantees or a complete source-launch
benchmark; normal HCI setup, emission, shutdown and process closure remain
physical measurements.

The [prospective protocol](../../research/native-direct-source-comparison.md)
loads the exact Nix archive once before the native parent starts. It derives
the expected immutable image ID from archive metadata/configuration and
requires the loaded tag to resolve to that ID. Every source then verifies the
same current tag/ID and launches by immutable ID. A missing or mismatched ID
fails without reload, fallback or transmission. The wrapper's usual default
loading path remains available for other callers.

This removes repeated image loading from the 90-second observation while
keeping all six RF conditions, OFF intervals and deadlines fixed. An actual
overrun still fails and is retained; no shortened episode or timing-limit
change is inferred from these host timings. The prospective caller and actual
archive-to-ID guard need independent review before another physical run.
# Exact archive-to-image preload check

The sole operator ran the frozen v3 preload function through locked Nix and
Task, before starting any native observer. The [actual receipt](exact-preload.json)
records the 90,619,442-byte archive, its SHA-256, configuration digest, selected
immutable image ID and exact match. Hashing, metadata checks and loading took
1.852097364 seconds. This opened no HCI or UART handles and launched no source
container. The six-source physical timing gate remains unverified.
