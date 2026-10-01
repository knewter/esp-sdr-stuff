#!/usr/bin/env python3
"""Plot actual rtl_test interval rate estimates and observed stop times."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    data = json.loads((args.folder / "capture.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    for run in data["runs"]:
        rate = run["requested_rate_hz"]
        label = f"{rate / 1e6:g} MS/s"
        offsets = [(sample_rate/rate-1)*1e6 for sample_rate in run["sample_rate_observations_hz"]]
        axes[0].plot(range(1, len(offsets)+1), offsets, marker="o", label=label)
        axes[1].barh(label, run["observed_stream_before_sigint_s"])
    axes[0].axhline(0, color="gray", linewidth=0.6)
    axes[0].set(xlabel="Reported approximately 10-second interval", ylabel="USB interval delivery estimate vs requested (ppm)")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.2)
    axes[1].axvline(60, color="black", linestyle="--", linewidth=0.7)
    axes[1].set(xlabel="Seconds from async-start message to SIGINT", xlim=(0, 75))
    fig.suptitle("Attached RTL-SDR Blog V4: internal-pattern transport measurements")
    fig.text(.5, -.015, "Interval jitter is not a calibrated oscillator measurement. Loss lower bounds are in the logs.", ha="center", fontsize=8)
    fig.savefig(args.folder / "continuity.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
