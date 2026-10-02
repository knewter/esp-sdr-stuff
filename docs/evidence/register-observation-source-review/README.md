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
