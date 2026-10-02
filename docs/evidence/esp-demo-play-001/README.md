# Interactive ESP spectrum session

October 2, 2026: the user viewed this local interactive session and reported
that it looked great. The unchanged verified receiver completed 60.005024
seconds with 2,706 valid spectrum frames and matching terminal totals.
All 4,194,304 bytes of restored flash match the preserved original; the
expected original application and GPIO boot markers were observed.

The [demo receipt](demo.json), [spectrum receipt](spectrum.json),
[initial flash comparison](before-install.json) and
[restoration receipt](restoration.json) record the physical results.
The independent review separately checks each raw CRC, sequence, CSV row,
terminal total, flash hash and original boot transcript.

This is the localhost UART-bridge spectrum viewer, with a Start button and
fixed session settings: 2412 MHz, nominal 80 MS/s, 512 bins, eight separate
FFT windows averaged per update, hardware AGC, 921600 baud and 60 seconds.
It has no interactive tuning or signal decoding controls. Power codes are
uncalibrated, with capture gaps; the plot does not identify signals.
The owned viewer closes before automatic restoration. No live service remains
after completion. [Repeat command and lifecycle](../../research/esp-sdr-demo.md).

The complete generated CSV and both actual viewer screenshots are retained
privately, together with the raw UART and flash reads. Their independent-review
receipt records exact sizes and hashes. They are excluded from this site's
small source-export budget; earlier published demo screenshots remain available.
