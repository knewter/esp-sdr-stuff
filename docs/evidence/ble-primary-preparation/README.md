# BLE primary-header preparation: host checks pass, RF remains unverified

The separate `extended-primary-zero-data-v1` parser/source preparation passes
89 scoped host checks and independent review. This record contains no hardware
operation, activated source, received waveform or RF acceptance. The
[manifest](manifest.json) pins code, tests, commits and limits; the
[prospective protocol](../../research/ble-extended-primary-zero-data-protocol.md)
defines the future controls. Legacy255 and original Trial B gates stay open.

Implementation `84421b5` adds a CRC-valid type7 `ADV_EXT_IND` parser and a
source flag requiring extended mode, handle1, map37-only, LE1M,20ms,
MaxEvents100,duration5000ms and zero host AD. That profile is tested offline;
its actual controller acceptance, primary layout and reception are unverified.
The unchanged legacy decoder remains SHA256 `834fdd78…130128`.

Ownership needs a present, exact private public AdvA, matching address type
and SID0 if ADI is present. Missing AdvA, ADI-only identification and auxiliary
AD cannot establish primary ownership. Zero data does not force the controller
to omit AUX or place AdvA in the primary. A with-AUX packet verifies the known
address/header subset; controller-selected DID/AuxPtr/power values are not
independently known full payload. Header bounds/flags/RFU/field combinations,
full24-bit protected CRC and nominal complete packet window are checked.
The unchanged bounded receiver search trains only on the public access
address; ownership cannot choose or repair a slicing hypothesis.

Independent review found a real defect after the original88 tests passed:
CRC-valid AuxPtr offsets could violate minimum timing or use invalid units.
Reviewer-authored `18ff4c2` fixes it, followed by the author's independent
specification read and89-test replay. Nonzero offsets must cover the actual
LE1M packet plus300µs;300µs units require at least245700µs. The valid
zero-offset/30µs special case stays allowed. These checks follow
[Core5.4 Vol6B2.3.4.5 and4.1.2](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-54/out/en/low-energy-controller/link-layer-specification.html).

Validation consists of19 primary-parser,6 primary-source,16 existing decoder,
33 existing direct-source and15 existing container tests. Synthetic primary
fixtures use independent reflected CRC/register whitening verified against
[the published SIG legacy sample](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core_v6.3/out/en/low-energy-controller/sample-data.html).
Six additional independent probes check corruption of every protected bit,
full AuxOffset/CA handling, unchanged legacy command bytes, new fixed wire
encodings, sanitized monitor output and unchanged legacy module globals.
Independent receipt SHA256 is recorded in the manifest; private artifacts and
addresses are excluded. Synthetic modulation proves host behavior, not RF.

The future denominator unit is controller-reported completed extended
advertising events, distinct from independently counted primary air packets.
Map37-only permits at most one primary PDU per event; individual PDUs or
entire events can be omitted for other functionality.
[Core6.2 Vol6B4.4.2.1/4.4.2.2](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/low-energy-controller/link-layer-specification.html)
requires that distinction. Counter applicability, full source/monitor receipts,
whole guarded capture windows, deduplication and independent waveform
reconstruction must precede any rate or counted-emission claim. N−verified
complete hits remains unresolved reception, including capture gaps,
truncation, source omission and decoder uncertainty; it is not confirmed RF
misses. The existing
[source-only count100 result](../ble-extended-count-limit-100-readiness-review/README.md)
used auxiliary AD and does not qualify this new zero-data primary profile.

The current monitor independently retains map/PHY/properties/data length,
interval,enable/count/duration and command acknowledgements. It omits some
source fields, including OwnAddrType,SID,skip,filter,scan notification and
fragmentation preference. Full wire construction is verified in host tests;
those omitted fields are not silently called independent physical observations.
No hardware checkbox, accepted spec, sensitivity/calibration or continuous
reception capability changes here.
