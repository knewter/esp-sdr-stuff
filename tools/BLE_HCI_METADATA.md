# Redacted extended advertising wire records

`ble_hci_monitor.py` parses commands independently of the transmitting source
helper. Opcode `0x2036` accepts exactly the 25-byte v1 layout and adds observed
Own/Peer address **types**, filter policy, requested power (including the
no-preference sentinel), secondary skip, SID, notification, exact interval units,
and explicit ignored-field semantics. The six peer-address bytes are discarded;
only `peer_address_is_zero` survives. No address, address digest, raw advertising
bytes, or foreign payload is retained.

This sanitizer pins the supported property envelope to Bluetooth Core 5.4.
It checks defined ranges, channel bits, ordering, legacy property combinations,
and PHY constraints. High-duty legacy intervals and legacy secondary PHY are
explicitly ignored. Newer decision-advertising properties and `0x207f` v2 are
outside this envelope. The existing legacy `0x2006` record shape is unchanged;
extended records add keys to existing fields. Older receipts lacking these keys
cannot prove the newly exposed fields and must remain unchanged.

Opcode `0x2037` now retains the actual fragment preference. Length, handle,
operation, preference, and empty-fragment constraints are checked. Data remains
redacted; partial/unchanged operations never claim a complete owned marker.
Refused commands do not become profile evidence; separately observed controller
completion errors remain errors. The parser does not infer controller state or
associate acknowledgements with commands.

Future primary-profile validation must compare **every** required record field
against its frozen profile, pair successful acknowledgements and scoped cleanup,
and preserve the complete monitor interval. A requested PHY, empty data, or SID
does not prove an emitted PDU, AdvA presence, ownership, or primary air count.
Original reception/count gates are unchanged. This change has no hardware test.

The independent fixtures and byte mutations are in
[`test_ble_hci_extended_fields.py`](../tests/test_ble_hci_extended_fields.py),
including fragmented pcap transport, redaction, refusal, boundary and source
encoder regressions. Author validation: 134 host-only checks with the locked CI
shell and a private Taskfile; no device, capture or container operation.

Primary source: [Bluetooth Core 5.4, Vol 4 Part E §7.8.53 and §7.8.54](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-54/out/en/host-controller-interface/host-controller-interface-functional-specification.html).

The source-only zero-data readiness profile additionally requires the v1
`0x2036` successful CommandComplete return's signed controller-selected transmit
power. The sanitizer now requires exactly five return bytes (command credit,
opcode, status and power) for success, accepting power −127 through20dBm.
Malformed/truncated/overlong or reserved successful returns are discarded.
A failed command permits the native source's four/five-byte envelope, retaining
its earlier status-only shape and discarding undefined failure power. Other
opcodes preserve their record shape. This observed controller-selected value is
separate from requested127/no preference and is not calibrated radiated power.
[Core6.2 Vol4E7.8.53](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-62/out/en/host-controller-interface/host-controller-interface-functional-specification.html)
defines these v1 return parameters. Older receipts remain unchanged; only
future frozen monitors contain the new successful-return field.
