# Fuller redacted HCI metadata: independently reviewed preparation

The host parser now retains independently observed v1 extended-advertising
command fields needed to validate the separate primary-source profile: address
**types**, zero-peer boolean, filter policy, requested power/no-preference,
secondary skip, SID, scan-request notification, exact interval units and data
fragmentation preference. Foreign peer bytes, addresses, payloads and address
hashes are discarded. The existing legacy record shape stays unchanged.

Independent review replays **134 focused host checks** and **23 separate probe
groups with 5,798 fixture cases**, covering offsets/endian/sign, byte ranges,
redaction, legacy compatibility, fragments, malformed records and actual chunked
pcap transport. The [sanitized receipt](checks.json) binds committed sources and
private review. This is tested preparation; it is not a physical source trial.

See the [supported envelope and implementation](../../../tools/BLE_HCI_METADATA.md)
and [primary-source protocol](../../research/ble-extended-primary-zero-data-protocol.md).
The parser pins Core5.4's v1 command layout and refuses unsupported fields.
Controller state, ignored values, acknowledgements and cleanup still need
profile-specific validation. Requested power or PHY never proves radiation,
emitted PHY, primary layout, ownership or an air count.

The completed original eight-bit and ten-bit controls used the older host HCI
helper and retain their original frozen bytes. Merging this parser after those
trials does not upgrade their receipts or verify omitted fields. Future input
freezes bind the new helper; no accepted RF requirement or task checkbox changes.
