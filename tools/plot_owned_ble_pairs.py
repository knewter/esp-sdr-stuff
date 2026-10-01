#!/usr/bin/env python3
"""Align same-host source-control timestamps with anonymous RF statistics."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receiver", type=Path)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    receiver = json.loads((args.receiver / "manifest.json").read_text())
    source = json.loads(args.source.read_text())
    rows = list(csv.DictReader((args.receiver / "captures.csv").open()))
    start = receiver["acquisition_ready_monotonic_ns"]
    plt.rcParams.update({"svg.fonttype": "none", "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(12, 4.5), layout="constrained")
    ax.scatter([(int(r["command_start_ns"]) - start) / 1e9 for r in rows],
               [float(r["channel_to_background_db"]) for r in rows], s=10, color="#4777c6", label="CRC-valid snapshot channel/background")
    pairs = []
    previous_off = start
    for episode in source["episodes"]:
        on = episode["registration_accepted_monotonic_ns"]
        off_request = episode["unregister_requested_monotonic_ns"]
        off_accepted = episode["unregistration_accepted_monotonic_ns"]
        ax.axvspan((on - start) / 1e9, (off_request - start) / 1e9, color="#57b890", alpha=.18)
        record = {"episode": episode["index"], "transition_margin_seconds": 2, "intervals": {}}
        for name, lo, hi in (("source_off_before", previous_off, on), ("source_registered", on, off_request)):
            selected = [r for r in rows if r["crc_and_count_valid"] == "True" and
                        int(r["command_start_ns"]) > lo + 2_000_000_000 and
                        int(r["header_received_ns"]) < hi - 2_000_000_000]
            values = [float(r["channel_to_background_db"]) for r in selected]
            record["intervals"][name] = {"snapshots": len(selected),
                "capture_indices": [int(r["capture_index"]) for r in selected],
                "median_channel_to_background_db": float(np.median(values)) if values else None,
                "p95_channel_to_background_db": float(np.percentile(values, 95)) if values else None,
                "maximum_channel_to_background_db": max(values) if values else None}
        pairs.append(record); previous_off = off_accepted
    ax.set(xlabel="Receiver host time since acquisition readiness (s)",
           ylabel="Mean PSD: 2401.5–2402.5 MHz / nearby background (dB)",
           title="Physical snapshots during three commanded BLE source episodes")
    ax.legend(fontsize=8); ax.grid(alpha=.15)
    fig.savefig(args.receiver / "source-pairs.svg", metadata={"Date": None})
    (args.receiver / "pair-summary.json").write_text(json.dumps({"pairs": pairs,
        "source_control_only": True,
        "note": "Shaded intervals indicate accepted BlueZ registration, not independently measured RF start/stop. Two-second transition margins. Relative PSD is neither calibrated power nor packet detection; emissions and missed events are uncounted."}, indent=2) + "\n")


if __name__ == "__main__":
    main()
