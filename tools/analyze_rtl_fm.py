#!/usr/bin/env python3
"""Inspect unsigned 8-bit IQ and quadrature FM structure; no station claim."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy import signal


def analyze_samples(raw, meta):
    if len(raw) % 2 or len(raw) < 2*meta["sample_rate_hz"]:
        raise ValueError("Capture is not whole IQ pairs or is shorter than one second")
    iq = (raw[::2].astype(np.float32)-127.5)/128 + 1j*(raw[1::2].astype(np.float32)-127.5)/128
    rate = meta["sample_rate_hz"]
    offset = meta["candidate_channel_hz"]-meta["center_hz"]
    mixed = iq*np.exp(-2j*np.pi*offset/rate*np.arange(len(iq)))
    taps = signal.firwin(255, 90000, fs=rate)
    channel = signal.resample_poly(mixed, 1, 4, window=taps)
    audio_rate = rate/4
    deviation = np.angle(channel[1:]*np.conjugate(channel[:-1]))*audio_rate/(2*np.pi)
    deviation = deviation[int(.1*audio_rate):]
    freq, psd = signal.welch(deviation, fs=audio_rate, nperseg=65536)
    spectrum_db = 10*np.log10(np.maximum(psd, 1e-20))
    pilot_region = (freq > 18980) & (freq < 19020)
    nearby = ((freq > 18500) & (freq < 18800)) | ((freq > 19200) & (freq < 19500))
    pilot_index = np.flatnonzero(pilot_region)[np.argmax(spectrum_db[pilot_region])]
    result = {
        "dependency_versions": {"numpy": np.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__},
        "iq_pairs": len(iq), "nominal_iq_duration_s": len(iq)/rate,
        "endpoint_byte_fraction": float(np.mean((raw <= 1) | (raw >= 254))),
        "demodulator": "quadrature phase difference; 255-tap 90kHz lowpass; decimate4; discard first100ms",
        "pilot_region_peak_hz": float(freq[pilot_index]),
        "pilot_region_peak_vs_nearby_median_db": float(spectrum_db[pilot_index]-np.median(spectrum_db[nearby])),
        "limitations": "Uncalibrated signal, antenna and station unknown; pilot-region feature alone is not known-source application proof or decoder validation",
    }
    return result, freq, spectrum_db, deviation, audio_rate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iq", type=Path, required=True)
    parser.add_argument("--folder", type=Path, required=True)
    args = parser.parse_args()
    meta = json.loads((args.folder / "iq-capture.json").read_text())
    raw = np.fromfile(args.iq, dtype=np.uint8)
    result, freq, spectrum_db, deviation, audio_rate = analyze_samples(raw, meta)
    (args.folder / "fm-analysis.json").write_text(json.dumps(result, indent=2)+"\n")
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), layout="constrained")
    axes[0].plot(freq/1000, spectrum_db)
    for marker in [19, 38, 57]:
        axes[0].axvline(marker, color="gray", linewidth=.7, linestyle="--")
    axes[0].set(xlim=(0, 75), xlabel="Demodulated frequency (kHz)", ylabel="Relative PSD (uncalibrated dB)", title="101.1 MHz candidate: quadrature-demodulated structure")
    axes[0].grid(alpha=.2)
    f, t, s = signal.spectrogram(deviation, fs=audio_rate, nperseg=8192, noverlap=4096)
    selected = f <= 75000
    axes[1].pcolormesh(t, f[selected]/1000, 10*np.log10(np.maximum(s[selected], 1e-20)), shading="auto", cmap="viridis")
    axes[1].set(xlabel="Time after initial 100 ms discarded (s)", ylabel="Demodulated frequency (kHz)")
    fig.suptitle("Measured RTL-SDR V4 IQ: antenna and station identity unverified")
    fig.savefig(args.folder / "fm-structure.png", dpi=160)
    plt.close(fig)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
