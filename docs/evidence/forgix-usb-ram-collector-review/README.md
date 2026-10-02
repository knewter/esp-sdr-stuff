# Independent synthetic collector review

Offline review passes collector revision `8e274ea967276e91b503112296e5a437b8acd596`.
This reviewer authored the RAM producer, not this collector. All 37 collector
tests were independently repeated through a private Task fixture in locked Nix.
No USB, serial, loading, reset, Docker or programming operation ran.

The parser matches the actual producer's 512-byte header, CRC32, nonce,
deterministic 460-byte payload, source-set/profile binding and pre-enqueue
control snapshots. `generated = enqueued + discarded + 1`; END reconciles
received frames and device-discard sequence gaps. Sampled queue backlog is
reported separately from host delivery. A loss-accounted run with device
discard is distinguished from verified zero-record-loss qualification.

Review identified and the author corrected symlinked private output roots,
storage-prefix count/hash honesty, consumed late-read retention, pre-START
deadline checks and the 20-second CONFIG edge. Final tests also cover the
85-second acceptance bound across read exceptions, parsing, START writes,
finalization, close and private persistence. Failed prefixes remain failed;
no resynchronization or retries hide damaged bytes.

The collector inspects the inherited exclusive lifecycle flock without
acquiring, releasing or closing it. It checks exact selected topology/product
and tty ancestry before and after exclusive serial open. It does not load or
recover firmware; those remain separate lifecycle prerequisites. Synthetic
fixtures prove software behavior, not enumeration, throughput or physical
recovery. No acceptance gate changed.
