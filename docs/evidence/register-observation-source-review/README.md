# Initial register-observation source and build review

**NOT installation-approved.** Candidate 001's build integrity checks pass,
but this checkpoint does not accept the complete diagnostic source, an
installer/lifecycle, or hardware behavior. No device or Docker operation was
performed. Source corrections and a fresh corrected build require further
review before installation.

- [Initial source checks](source-checks.json) record actual locked-Nix/Task
  executions, independent synthetic packing and malformed-receipt cases.
- [Candidate 001 build checks](artifact001-checks.json) record independent
  hashes, layout, buffer ranges, image checksums/digests and SDK source NAR.
- [First firmware guard correction](guard-correction-checks.json) records the
  separately committed correction and the malformed-BEGIN edge found next.
- [BEGIN guard follow-up](begin-correction-checks.json) records the subsequent
  correction and independent byte-length replay.
- [Prospective protocol](../../research/receiver-register-observation-protocol.md)
  supplies the acceptance contract; this receipt does not change it.

The initial reviewed source is contained in root commit
`85c0289d11fea0c75759b2679eb8a7692a18f6fa`, including the isolated receiver
overlay/builder and strict host receipt parser. Receiver base remains
`550fadea4d00a9e26ce921c5832167becb3dc20c`; SDK remains
`25fe69f946311abdaf9ad56591f25fedbc20ac98`. The diagnostic INFO/profile is
separate from the normal SDR artifact. The fixed requested settings are LO
2401 MHz, bandwidth 20 MHz/filter code 64, manual selector 48, nominal 16 MS/s,
10-bit components and twenty 16,380-pair captures. No source was operated.

The four hooks match the declared entry, armed-before-trigger, dump-complete
and restored-after-dump boundaries. Each reads RX_GAIN once, extracts only
bits24–30 and bit23, and brackets that read with firmware times. The overlay
adds no gain or other RF write. The actual-C fixture traces the original dump,
SRAM, byte-selection and filter operations, including cleanup before UART;
it does not substitute a simulated acquisition function for `acquire_iq`.
MMIO, clock, PHY/filter APIs and transport drivers are controlled host shims.
These are software checks, not target timing or reception proof.

The reviewer actually ran `nix develop .#ci --command task register:check`:
**26 tests passed**. An additional independent contiguous 40-bit unpack of
the actual generated C output checked **all 327,600 pairs**, including both
10-bit components, against the fixture's separately supplied sample pattern.
This verifies synthetic packing/count/CRC/order, not RF content.

Concrete initial findings:

1. The original app-loop parser-error branch could leave an armed diagnostic
   active after an overlong command and append `ERR command_length` after a
   partial binary transfer. The new loop needed the same session and broken-wire
   guards as normal command dispatch.
2. An actual byte-length UART shim supplied armed bytes
   `CAP20 16380 6\0trailing\n`. The unchanged generated common parser returned
   status 1, triggered one acquisition and remained armed: C-string handling
   discarded the bytes following the embedded NUL. The older fixture used
   `strlen` for input and could not represent this stream.
3. Mutating the actual C deadline-failure receipt to `records=[]`, with a
   complete CRC-valid DATA tuple, was accepted as a failed receipt. The same
   receipt/DATA was also accepted before configuration in a new host Session.
   Both stayed failed; neither bypassed successful-completion gates. A failed
   receipt without DATA additionally accepted count 32,768 although the source
   masks the actual hardware count to 15 bits. These are contradictory failed
   observation metadata, not successful reception.

The author committed first firmware correction
`5e397877c8cc06013c5c7a7b0d6b62026e98fdea`. The reviewer independently ran its
**21 C/builder tests** and inspected/replayed the actual transport cases.
Armed overlong/NUL commands now produce only config plus failure, without an
acquisition. After partial DATA, both malformed inputs leave exactly the
17-byte prefix and append no bytes. Ordinary unarmed behavior remains intact.
However, an additional actual byte-length test still armed NEW state with
`REGOBS1 BEGIN <valid nonce>\0trailing\n`; the guard bypassed every NEW-state
command. Newly introduced BEGIN has no upstream behavior to preserve and must
reject this malformed input. The author then committed
`029014e0c8a362efdcf842a1e684a821ecd2199b`. Its **22 C/builder tests** passed
under the reviewer's Nix/Task execution, and the independently modified actual
transport fixture now reports that malformed BEGIN does not arm. The armed
malformed-input and partial-DATA suppression cases still pass. These source
corrections do not update or approve candidate 001.

Candidate 001 is retained independently of these source changes. Its manifest
SHA-256 is
`219a69bc752613c30da56c9bc93959d1675b568929e227ea5900ffd9764f90d2`.
The reviewer rehashed committed firmware/builder inputs and actual prepared
source, configuration, map, ELF and all three image parts. Independent image
segment XOR checksums, appended SHA-256 digests, ESP32/DIO/40 MHz/2 MB headers,
application descriptor/version, partition entries and partition MD5 all pass.
The SDK source NAR was independently rehashed to its exact fixed value.

The linked record array is **1,944 bytes = 81 × 24**; JSON and wire buffers
are 2,048 bytes each. Their actual linked ranges are disjoint and below
`0x3ffe8000`, outside the entire reserved sample slab
`[0x3ffe8000,0x3fff8000)`. Candidate 001 was built before the command fixes and
remains unapproved even though those build checks pass.

Remaining prerequisites are independent acceptance of the complete corrected
source, including the host failed-receipt guards, a fresh committed-source build
and independent artifact review, and a separate
reviewed manifest guard plus identity/exclusivity/preservation/cancellation/
process-group/full-restoration lifecycle. No persistence/lifecycle fault
injection or physical stage readback has been completed by this checkpoint.
No selector continuity, effective analog gain, tuning, sensitivity, SDR packet,
source-event count or Trial B qualification is claimed.

## Corrected source and worker checkpoint

Root revision `3beae7203825f1922e43eb5fa8946494f614d18a` is a reviewed,
committed software checkpoint. **Installation remains unapproved.** Exact
source hashes, test counts and remaining prerequisites are recorded in
[corrected-checkpoint.json](corrected-checkpoint.json). The reviewer independently
ran the locked Nix/Task register check: **55 tests passed** (22 actual-C/builder,
11 artifact, 11 receipt and 11 worker tests). No device or Docker was used.

The three original contradictory failed-receipt mutations now reject before
records are accepted; the independent 327,600-pair synthetic unpack still
passes. See [failed-receipt corrections](failed-receipt-corrections.json).
Another independently reproduced inconsistency made a completed session claim
a 50-second capture inside a roughly nine-second firmware session. The new
guard requires elapsed time to fit between the armed-read end and dump-complete
read start. Both successful and failed actual-C receipts reject that mutation
and the enclosing bound plus one; ordinary receipts retain their status. See
[elapsed checks](elapsed-correction-checks.json).

An additional end-to-end worker replay used the actual C deadline-failure
response after a complete CRC-valid 40,950-byte DATA payload. The worker retains
that payload and five available records as **failed**, accepts zero captures,
aborts after the single CAP command and sends no END. Saved bytes were verified
after UART closure. See [failed DATA worker checks](failed-data-worker-checks.json).
The worker also bounds write timeouts to the remaining absolute budget and
requires an explicitly observed closed UART before persisting raw buffers.
An unconfirmed close returns failed metadata without worker disk persistence;
the future supervisor must independently establish whole-group closure.

The separate [artifact guard checks](artifact-guard-checks.json) pass against
candidate 001's actual component files: ELF allocation boundaries, map/symbols,
ELF-to-image loaded bytes, canonical partition MD5, generated flash arguments,
image checksums/digests and actual pinned SDK source NAR. Independently moving
actual ELF LOAD addresses into the MAC slab and its instruction alias rejects.
The pinned SDK maps the two sample banks to instruction addresses covering
`[0x400a8000,0x400b8000)`; both aliases are excluded from application allocations.
The whole new artifact guard **rejects candidate 001's stale source**, as required.
A fresh build must export the exact reviewed ELF, symbol list and flasher arguments.

The current `read_end_us − read_begin_us` fields measure a nominal bracket around
the MMIO read, including timestamp-call boundary effects. They omit surrounding
hook work and do **not** satisfy a claim of measured full-hook added cost. That
measurement is being revised prospectively and requires another source/build
review. This checkpoint also does not approve an installation/restoration
supervisor, target behavior, physical timing, effective analog gain, reception
or counted source events. The original RF and Trial B gates remain unchanged.

## Fresh artifact and corrected lifecycle preflight

[Latest preflight checks](latest-preflight-checks.json) record the subsequent
review of committed caller bytes at `f84d94a` / documentation-only `f77cb97`:
**75 locked-Nix/Task tests pass**. Exact artifact 002 has manifest SHA-256
`7b09e894cc2d2673adb94afb3eb245a06a91b26efd91c566e28f81816cf9ef83`
and was built from `bf96681a9382367bfb759ee658d42392c4b1b9fe`.
The reviewer ran its whole artifact guard and independently verified actual
source/part hashes, image XOR/SHA, canonical partition MD5 and SDK source NAR.
Actual records occupy **2,592 bytes = 81 × 32**, outside both reserved sample
memory aliases; serialization buffers remain 2,048 bytes each. Candidate 001
remains stale and unapproved.

The compiled five CCOUNT pairs enclose the separate, non-inlined body call:
entry/return, prechecks, pointer lookup, both timer calls, the one MMIO read and
original field stores. The reviewer compared 246 disassembled instructions
with the actual ELF bytes. Stage argument setup and the initial counter spill
are inside the observed bracket. Boundary costs, the subsequent branch/delta/
final cycle store, initial reload and surrounding caller work remain residual.
Raw cycles include interruptions/preemption and retain whole-counter-period
ambiguity; this proves compiled coverage, not calibrated total perturbation.
The [author's compiled audit](../register-observation-cycle-review/README.md)
provides the bounded instruction excerpt and is separately labelled.

The lifecycle holds the common lock, requires the original full-flash baseline
before installing, rejects unknown fuser outcomes, and closes the complete
owned process group before restoration or parent pipe persistence. Unknown
closure blocks restoration. The independently replayed original wire now
supplies its actual receipt CRCs and exact DATA boundaries; successful END
must consume all retained protocol bytes. Cancellation, dual real pipes,
output/deadline failures and restoration policy have software fault checks.

Actual trial 001 retained a **failed supervisor** result despite a completed
worker. Its first startup newline occurred at offset 8,903, before the first
diagnostic line at 9,102; a diagnostic-line limit had been applied to that
uninterpreted startup span. Independent replay verifies all **20 payloads,
22 original receipts and 81 records**, with all post-config bytes consumed.
The worker took 10.500512627 seconds. The before-install and restored images
both contain the original 4 MiB hash, and direct private boot inspection confirms
the original application, SDK and both GPIO states. This is reset recovery,
not electrical power-cycle proof. The original failed lifecycle is preserved.

The prospective correction permits only bounded startup spans before the
first diagnostic candidate. It retains the strict 2,048-byte receipt limit,
original CRCs and binary boundaries, with no protocol resynchronization.
The reviewer conditionally cleared one fresh bounded experiment using exact
artifact 002 and fresh identity/fuser/lock/full-baseline checks. Physical timing
and stage observations still need their actual review. No effective analog
gain, reception, source-event denominator or Trial B gate is accepted here.
