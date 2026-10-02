# First physical register observation: failed supervisor validation

**This lifecycle remains failed.** The separately approved candidate002 ran
through the frozen `27ec089` supervisor on 2026-10-02. The worker recorded
20 captures and 81 stages in 10.500512627 seconds, but the supervisor rejected
its saved-wire parser before publishing a capture receipt. All private UART,
IQ and worker metadata remain retained for independent review.

The first retained startup newline follows 8,903 bytes; the first actual
diagnostic configuration line starts at byte offset 9,101. The supervisor
incorrectly applied the 2,048-byte diagnostic-line limit to that startup
prelude. This failure was independently reproduced using numeric offsets,
without publishing boot bytes. The prospective correction allows finite
private startup noise within the worker RAM budget before the first diagnostic
candidate, while preserving exact protocol framing, metadata CRCs, binary
boundaries and all subsequent line limits. A later offline replay does not
change this run's failed lifecycle status.

[Before-install read](before-install.json) matches the preserved full 4 MiB.
[Restoration](restoration.json) independently reads all 4 MiB with SHA-256
`6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`
and observes the original application, SDK and both GPIO states after reset.
[Lifecycle](register-observation.json) records the failure and verified
restoration. No electrical power-removal, calibrated gain, RF reception or
transmitted-count claim follows.

Artifact manifest SHA-256:
`7b09e894cc2d2673adb94afb3eb245a06a91b26efd91c566e28f81816cf9ef83`.
The [declared protocol](../../research/receiver-register-observation-protocol.md)
and [source review](../register-observation-source-review/README.md) retain
the original finite trial and acceptance limits.
