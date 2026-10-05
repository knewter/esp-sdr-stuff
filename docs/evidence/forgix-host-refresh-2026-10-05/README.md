# Fresh Forgix host preparation

October 5, 2026: **PASS for saved artifact and host-runtime preparation only**.
[Checks and pinned hashes](checks.json) bind source `c4aedd1`, a fresh actual
configuration006 build at `dc23be8`, and independent review.

All 19 register build-source bytes match the refreshed source. The ELF embeds
the retained 173,380-byte FPGA image and uses 203,700 SRAM bytes including a
4 KiB stack. Review checks startup/reset, watchdog and UID ordering, PIO and
configuration handoff, with nine malformed-ELF cases. The firmware project sources are unchanged:
all 196,832 loadable bytes equal configuration005 after normalizing its single
64-byte compiled source identity. The earlier 30 actual-C tests remain historical.

Fresh root snapshots bind 36 register inputs, 65 synthetic inputs, seven host
tools, and actual content verification of all 268 Nix paths and 1,097 edges.
Independent saved review joins source maps, imports, tools, archives and the
whole graph to root-observed terminal exits. A real inherited-lock worker uses
two complete 2 MiB **fixture** baseline copies and an injected device boundary.
Synthetic ARM001 remains bound under its unchanged historical-build policy.

No FPGA was programmed; registries stay empty. The runtime record retains a
historical Docker image identity, with no fresh daemon inspection. A new read-only USB survey at13:11:12 UTC still finds no matching Forgix;
the ESP stable link, preserved backup bytes and one RTL-SDR remain present.
It holds the operator lock and opens no serial/USB device. Matching attachment, fresh preservation and
current operator admission still precede the clock diagnostic; electrical
timing, register readback and several-rate FPGA transport remain unmeasured.
Internal tests need no ESP wiring. Private artifacts and identities stay unpublished.

The [finalization review](../forgix-synthetic-finalization-review/README.md),
[historical register checkpoint](../forgix-register-production-checkpoint/README.md)
and [clock safety case](../forgix-clock-safety-case-preparation/README.md) retain
their separate scopes.
