#!/usr/bin/env python3
"""Plot actual redsea output; omitted groups and RF amplitude are not measured."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", required=True, type=Path)
    a = p.parse_args()
    rows = [json.loads(line) for line in (a.folder / "live-decoder.ndjson").read_text().splitlines()]
    rows = [r for r in rows if "time_from_start" in r]
    times = [r["time_from_start"] for r in rows]
    valid = [sum(b != "----" for b in r["raw_data"].split()) for r in rows]
    pi = [r["raw_data"].split()[0] == "9250" for r in rows]
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), layout="constrained", sharex=True)
    axes[0].plot(times, np.cumsum(valid), label="Direct checkword-valid blocks")
    axes[0].plot(times, np.cumsum(pi), label="Valid block A = PI 0x9250 (WXJC)")
    axes[0].set(ylabel="Cumulative decoded count")
    axes[0].legend()
    axes[1].scatter(times, valid, s=12, alpha=.65)
    axes[1].set(yticks=range(5), ylim=(-.2, 4.2), xlabel="Decoder time from MPX start (s)", ylabel="Valid blocks per emitted group")
    for ax in axes:
        ax.grid(alpha=.25)
    fig.suptitle("Measured 101.1 MHz RDS reception — redsea error correction disabled")
    fig.text(.5, -.015, "Counts cover emitted groups only; unsynchronized groups excluded. Antenna model unverified; no calibrated RF amplitude.", ha="center", fontsize=9)
    fig.savefig(a.folder / "rds-decoding.png", dpi=160, bbox_inches="tight")


if __name__ == "__main__":
    main()
