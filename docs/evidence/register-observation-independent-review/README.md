# Independent register diagnostic review

**PASS for completed trial 002 and recovery.** An offline reviewer independently
replayed the original saved UART and all 20 IQ files from the operator's run.
The [compact checks](checks.json) bind the reviewed evidence revision `c779ade`,
public file hashes, executed callers and unchanged candidate002 manifest.
The reviewer opened no device and performed no hardware operation.
The actual stage SVG was rendered with Nix Chromium and visually inspected;
its axes, legend, measured points and scope warnings agree with the replay.

All 22 original diagnostic JSON CRCs and 20 original DATA CRCs match. Exact
binary boundaries, each saved payload hash, all 327,600 independently unpacked
signed ten-bit I/Q pairs, 81 ordered stage records, acquisition timing and END
totals pass. Replay consumes every retained protocol byte after configuration.
The host acquisition took 10.522101644 seconds; the firmware session spanned
9,347,966 microseconds. Both are within the declared 30-second ceiling.

Every sampled stage read selector 48 and bit23=1. Hook-body observations range
323–4,008 modular cycles, median 325. Per-stage ranges are recorded in the
checks. These brackets include the compiled hook body; counter boundaries,
post-body arithmetic/store and surrounding caller residuals remain outside.
Interrupt/preemption, counter wrap and nominal timer/CPU limitations remain;
neither cycle counts nor read brackets are calibrated RF timestamps or total
instrumentation cost. The [compiled scope review](../register-observation-cycle-review/README.md)
and [source/artifact review](../register-observation-source-review/README.md)
document those limits.

The before-install and restored images each contain 4,194,304 bytes and match
the preserved original SHA-256 `6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`.
Direct private reset-boot text contains the original application/SDK and both
GPIO states. The completed lifecycle records owned worker closure and verified
restoration. This is reset recovery; no new power-cycle claim follows.

[Trial 001](../receiver-register-observation-001/README.md) remains **failed**:
its original supervisor rejected a long startup line. Its saved worker data and
restoration passed separate offline replay; that does not change the failed
lifecycle. The corrected startup parser was reviewed before the fresh
[trial 002](../receiver-register-observation-002/README.md).

This result establishes sampled register-field consistency for this bounded
run. It does not establish state between reads, effective analog gain,
calibrated sensitivity, BLE/SDR reception, an emitted-event denominator or
eligibility for Trial B. Raw UART/IQ, boot text, firmware images and detailed
analysis remain private. All original RF/count gates remain unchanged.
