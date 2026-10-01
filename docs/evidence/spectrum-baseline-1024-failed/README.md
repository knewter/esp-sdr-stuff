# First browser-spectrum trial: integrity failure

Physical trial, 2026-10-01. The requested 60-second, 1024-bin, 80 MS/s nominal
spectrum session failed at about 40.88 seconds after 2711 valid frames when a
spectrum payload failed CRC. The viewer stopped and closed its serial handle.
This does not satisfy the 60-second display gate.

[Results](results.json), [per-frame CSV](spectra.csv),
[browser observation](browser-observation.json), [live still](live-browser.png)
and [failed completion still](completed-browser.png) preserve the failed trial.
Private raw frames remain under ignored `.scratch/spectrum-baseline-raw/`.
The receiver and settings are recorded in the manifest. FFT power codes are
uncalibrated; no controlled source or signal identity is claimed.

The failure occurred during physical acquisition; its cause has not been
isolated. The next trial reduces output to 512 FFT bins. A subsequent success
would establish that bounded trial's integrity, without erasing this failure
or proving generally error-free spectrum transport.
