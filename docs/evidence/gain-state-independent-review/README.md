# Independent review of gain-state diagnostic 001

The [physical diagnostic](../gain-state-diagnostic-001/README.md) passes its
capture-integrity, deadline and original-firmware recovery checks. This review
used saved files only; the reviewer opened no device. Reviewed evidence commit:
`9816d7a63d6aa819aba388cf16ea41d18d8f3ad7`.

[Machine-readable checks](trial-001-checks.json) record an independent parse of
the private 829,527-byte RX wire and every payload. All twenty saved IQ files
equal their exact wire slices. Each contains 40,950 bytes and 16,380 pairs;
CRC32, SHA-256 and lengths agree with the public receipts. The complete protocol
suffix parses without trailing bytes, including the three setting ACKs and all
41 gain responses. Outgoing command names and order are established by frozen
executed source and typed time brackets, rather than a raw TX recording.

An independent scalar decoder unpacked each five-byte little-endian group into
four signed ten-bit components. Integer sums, squares, unique-code sets and
endpoint counts reproduce every published numerical statistic and all twenty
CSV rows. Median AC power is 70.646800 code²; capture 18's 40,759.552372 code²
outlier is retained. The source was uncontrolled, so these values do not identify
a transmitter or establish calibrated power, SNR or owned-packet reception.

All 41 responses report software MANUAL/index 48, startup maximum 72 and live
register bit23 equal to one. Before/after time brackets surround every capture.
Acquisition completed in 10.299817 seconds and every reply fits the 30-second
ceiling. The twenty nominal 1.02375 ms RF windows total 20.475 ms, with gaps.
These queries establish bit23 at their observation points, not continuously
during capture, and do not read the effective hardware gain index or gain in dB.
They do not rule out a transient or historical state change.

The installed Nix-built `550fade-uart921600` manifest, all three image hashes,
canonical offsets and actual installation receipt agree. Frozen executed helper
hashes and all six committed native-reference prerequisite hashes agree. The
UART worker and its owned groups closed before restoration. Independently
rehashing both the current-image read and restored read gives 4,194,304 bytes
with preserved original SHA-256
`6e8f0793916fa1d701415abc48c6ea91756cf864de8fdbf8459c181b08fc0974`.
Private reset-boot content contains the original application, SDK and both GPIO
messages. This is reset-boot recovery evidence, not a new power-cycle observation.

The actual published SVG was rendered and inspected. Its logarithmic code²
axis, all twenty points, sampled bit values and uncontrolled-source/coverage
limits agree with the data. The CSV, summary, public receipts and plot retain the
measurement's scope; raw wire, IQ, flash and identifying boot content remain
private. Public file hashes are recorded in the checks receipt.

No RF, protected-PDU or transmitted-event-count gate closes. The earlier SDR
nulls remain unresolved; this diagnostic and the native reference do not supply
Trial B's fresh SDR-positive prerequisite.
