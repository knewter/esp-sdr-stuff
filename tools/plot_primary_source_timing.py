#!/usr/bin/env python3
"""Plot hash-bound source-only host/HCI timing without exporting device identity."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lifecycle", type=Path, required=True)
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.lifecycle.read_bytes()
    checks = json.loads(args.checks.read_text())
    if (checks.get("result") != "PASS_SAVED_SOURCE_ONLY"
            or hashlib.sha256(raw).hexdigest() != checks["saved_trial_sha256"]["lifecycle.json"]
            or checks.get("air_primary_count") is not None or checks.get("RF_accepted") is not False):
        parser.error("Requires matching independently reviewed source-only checks")
    life = json.loads(raw)
    if life.get("status") != "controller_profile_qualified" or life.get("profile") != checks["profile"]:
        parser.error("Lifecycle profile/result does not match review")
    source = life["source"]
    count = source["actual_controller_completed_events"]
    if count != checks["verification"]["controller_completed_extended_events"]:
        parser.error("Recorded controller count does not match review")
    base = life["supervisor_started_monotonic_ns"]
    times = {name: (stamp - base) / 1e9 for name, stamp in {
        "Monitor ready": life["monitor_ready_monotonic_ns"],
        "Configuration": source["configuration_monotonic_ns"],
        "Enable ACK": source["enable_ack_monotonic_ns"],
        "Termination": source["termination_monotonic_ns"],
        "Socket closed": source["socket_closed_monotonic_ns"],
        "Supervisor result": life["supervisor_terminal_monotonic_ns"],
    }.items()}
    if not all(math.isfinite(t) and t >= 0 for t in times.values()) or list(times.values()) != sorted(times.values()):
        parser.error("Recorded timestamps are non-finite or out of order")
    interval = times["Termination"] - times["Enable ACK"]
    if (not math.isclose(interval, checks["seconds"]["enable_ack_to_term_seconds"], abs_tol=1e-9)
            or not math.isclose(times["Supervisor result"], checks["seconds"]["supervisor_seconds"], abs_tol=1e-9)):
        parser.error("Recorded intervals do not match review")

    plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "primary-source001",
                         "font.family": "DejaVu Sans", "font.size": 10})
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), gridspec_kw={"height_ratios": [1, 1.2]})
    fig.patch.set_facecolor("#101827")
    for ax in axes:
        ax.set_facecolor("#172336")
        ax.tick_params(colors="#cbd8e8")
        ax.set_yticks([])
        ax.set_ylim(-.5, .7)
        ax.grid(axis="x", alpha=.2, color="#9aafc9")
        for spine in ax.spines.values():
            spine.set_color("#405168")
    whole, zoom = axes
    whole.hlines(0, 0, times["Supervisor result"], color="#9aafc9", linewidth=2)
    whole.axvspan(times["Enable ACK"], times["Termination"], color="#73dda6", alpha=.35)
    for label, height in [("Monitor ready", .3), ("Enable ACK", -.3),
                          ("Termination", .3), ("Supervisor result", -.3)]:
        t = times[label]
        whole.scatter(t, 0, s=45, color="#73dda6", zorder=3)
        whole.annotate(f"{label}\n{t:.3f} s", (t, 0), xytext=(t, height),
                       ha="center", va="center", color="#e7eef7",
                       arrowprops={"arrowstyle": "-", "color": "#9aafc9"})
    whole.set_xlim(-1, times["Supervisor result"] + 3)
    whole.set_xlabel("Seconds since recorded supervisor start", color="#e7eef7")
    whole.set_title("Recorded source-only supervisor", color="#e7eef7", loc="left")
    anchor = times["Enable ACK"]
    zoom.hlines(0, times["Configuration"] - anchor, times["Socket closed"] - anchor,
                color="#73dda6", linewidth=4)
    for label, xtext, ytext in [("Configuration", -.05, .32), ("Enable ACK", .45, -.3),
                              ("Termination", 1.95, .32), ("Socket closed", 2.65, -.3)]:
        t = times[label] - anchor
        zoom.scatter(t, 0, s=45, color="#73dda6", zorder=3)
        zoom.annotate(f"{label}\n{t:+.6f} s", (t, 0), xytext=(xtext, ytext),
                      ha="center", va="center", color="#e7eef7",
                      arrowprops={"arrowstyle": "-", "color": "#9aafc9"})
    zoom.set_xlim(-.4, interval + .6)
    zoom.set_xlabel("Seconds relative to enable acknowledgement", color="#e7eef7")
    zoom.set_title(f"Enable ACK → termination: {interval:.6f} s · controller reports {count} completed events",
                   color="#e7eef7", loc="left")
    fig.suptitle("Zero-data source001 · actual host/HCI timing", color="#e7eef7", fontsize=16, y=.975)
    fig.text(.09, .025, "Source-only evidence: no individual RF emission times or ESP reception were measured.\n"
             "Supervisor result precedes final persistence. Process/container closure timestamps were not retained.\n"
             "Independent audit: 23 native / 11 monitor records; five ACK0 pairs; controller power response uncalibrated.",
             color="#cbd8e8", fontsize=9)
    fig.subplots_adjust(left=.09, right=.95, top=.86, bottom=.2, hspace=.65)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, metadata={"Date": None, "Description": "Measured relative host/HCI timing; no RF reception claim."})
    plt.close(fig)
    print(json.dumps({"result": "plotted", "lifecycle_sha256": hashlib.sha256(raw).hexdigest(),
                      "output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                      "RF_accepted": False}))


if __name__ == "__main__":
    main()
