#!/usr/bin/env python3
"""Plot measured transfer timing and nominal RF coverage from saved snapshots."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    results = json.loads((args.evidence / "results.json").read_text())
    rows = list(csv.DictReader((args.evidence / "snapshots.csv").open()))
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout="constrained")
    summary = []
    labels, coverage, colors = [], [], []
    for run in results["runs"]:
        selected = [r for r in rows if int(r["rate_hz"]) == run["rate_hz"] and
                    int(r["bits_per_component"]) == run["bits"] and r["status"] == "ok"]
        intervals = np.array([float(r["round_trip_ms"]) for r in selected])
        label = f'{run["rate_hz"] // 1000000} MS/s · {run["bits"]}-bit'
        color = "#16876a" if run["bits"] == 8 else "#4777c6"
        if len(intervals):
            axes[0].plot(np.sort(intervals), np.arange(1, len(intervals) + 1) / len(intervals),
                         label=label, linewidth=1.5)
        labels.append(label); coverage.append(run["nominal_coverage_fraction"] * 100); colors.append(color)
        summary.append({**run, "median_round_trip_ms": float(np.median(intervals)) if len(intervals) else None,
                        "p95_round_trip_ms": float(np.percentile(intervals, 95)) if len(intervals) else None,
                        "median_firmware_capture_us": float(np.median([float(r["firmware_capture_us"]) for r in selected])) if selected else None})
    axes[0].set(xlabel="Measured command-to-payload time (ms)", ylabel="Fraction of valid snapshots",
                title="Actual UART delivery time")
    axes[0].legend(fontsize=8); axes[0].grid(alpha=.15)
    axes[1].barh(labels, coverage, color=colors)
    axes[1].set(xlabel="Nominal RF window / measured series time (%)", title="Snapshot coverage, including gaps")
    axes[1].invert_yaxis(); axes[1].grid(axis="x", alpha=.15)
    for index, value in enumerate(coverage):
        axes[1].text(value, index, f" {value:.3f}%", va="center", fontsize=9)
    axes[1].set_xlim(0, max(coverage, default=1) * 1.35)
    fig.suptitle("Measured ESP32 snapshots · CP2102 UART at 921,600 baud")
    fig.savefig(args.evidence / "snapshot-timing.svg", metadata={"Date": None})
    (args.evidence / "summary.json").write_text(json.dumps({"runs": summary,
        "note": "RF coverage is calculated from advertised nominal rates; no calibrated ADC clock or capture-start timestamp."}, indent=2) + "\n")


if __name__ == "__main__":
    main()
