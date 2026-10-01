#!/usr/bin/env python3
"""Plot measured rtl_power sweep CSV without assuming calibrated dBm."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    rows = []
    with (args.folder / "fm-sweep.csv").open() as f:
        for row in csv.reader(f):
            low, step = float(row[2]), float(row[4])
            values = np.asarray(row[6:], dtype=float)
            frequencies = low + (np.arange(len(values))+.5)*step
            rows.append((row[0].strip()+" "+row[1].strip(), frequencies, values))
    if not rows:
        raise RuntimeError("No sweep rows were captured")
    timestamps = sorted(set(row[0] for row in rows))
    grid = np.linspace(88e6, 108e6, 2001)
    frames = []
    for stamp in timestamps:
        selected = [row for row in rows if row[0] == stamp]
        frequencies = np.concatenate([row[1] for row in selected])
        powers = np.concatenate([row[2] for row in selected])
        order = np.argsort(frequencies)
        frames.append(np.interp(grid, frequencies[order], powers[order], left=np.nan, right=np.nan))
    measured = np.asarray(frames)
    fig, ax = plt.subplots(figsize=(11, 4), layout="constrained")
    for frame in measured:
        ax.plot(grid/1e6, frame, alpha=.3, linewidth=.7, color="#159a8c")
    valid_columns = np.any(np.isfinite(measured), axis=0)
    median = np.full(len(grid), np.nan)
    median[valid_columns] = np.nanmedian(measured[:, valid_columns], axis=0)
    ax.plot(grid/1e6, median, color="#162b46", label="Median of sweep records")
    ax.set(xlabel="Frequency (MHz)", ylabel="rtl_power log-power units (uncalibrated)",
           title="Attached RTL-SDR V4: passive FM-band sweep, antenna/source unverified")
    ax.grid(alpha=.2)
    ax.legend()
    fig.savefig(args.folder / "fm-spectrum.png", dpi=160)
    plt.close(fig)
    print(f"{len(rows)} hop records, {len(timestamps)} timestamp groups; not simultaneous full-band captures")


if __name__ == "__main__":
    main()
