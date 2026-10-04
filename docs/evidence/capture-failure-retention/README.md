# Failed UART data is retained privately

Source preparation, October 4, 2026. [Checks](checks.json) record 88 focused
checks, seven independent checks and four actual spectrum START fault probes.
Independent caller integration also passes 34 caller checks, 26 monitor checks
and three probes. Historical successful capture and CSV bytes are unchanged.

The reader preserves bytes returned before a failed read, parsed headers,
expected lengths/CRC and request/header/failure brackets. Uncertain snapshot or
spectrum framing closes the serial path before private persistence and refuses
retry, resynchronization and RELEASE. Write/flush errors, partial or invalid
START replies and complete ERR replies are covered. Raw reply text is redacted
from public errors. Storage stays mode 0700/0600.

Repeat: `nix develop .#ci --command task capture:failure:test`.
See the [failure contract](../../../tools/ESP_SDR_FAILURE_RETENTION.md).

The [earlier failed episode](../ble-bluez-control-005-failed/README.md) remains
failed: its discarded fragment cannot be recovered by this later change.
Bytes consumed internally but never returned by a failing read remain unknown.
Fresh runtime/device input freezing, exclusive operation, full preservation and
verified restoration still precede each physical trial. This software review
supplies no reception result or emitted-event denominator.
