#!/usr/bin/env python3
"""Receive bounded private IQ while another operator controls the owned source."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from esp_sdr_capture import STABLE_PORT, open_board, synchronize, queries, settings, capture, numerical_stats, unpack, command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=200)
    parser.add_argument("--frequency", type=int, default=2401)
    parser.add_argument("--bandwidth", type=int, default=12)
    parser.add_argument("--gain", default="hardware")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 600:
        parser.error("seconds must be 1..600")
    private = args.private.resolve()
    if not any(p in {".scratch", "backups"} for p in private.parts) or any(p in {"site", "docs"} for p in private.parts):
        parser.error("private IQ requires ignored .scratch/ or backups/ outside published roots")
    args.output.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False, mode=0o700)
    record = {"kind": "physical owned-source capture; source controlled separately",
              "firmware_variant": "550fade-uart921600", "baud": 921600,
              "nominal_rate_hz": 16000000, "bits_per_component": 8, "samples": 16380,
              "frequency_mhz": args.frequency, "bandwidth_mhz": args.bandwidth, "gain": args.gain,
              "source_channel": 37, "source_frequency_mhz": 2402,
              "actual_RF_event_count": None, "requested_seconds": args.seconds,
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "limitations": "Nominal ADC rate; no calibrated power/frequency, hardware capture-start timestamp or emitted-event denominator. Absolute host monotonic timestamps permit same-machine source-log alignment."}
    rows = []
    p = open_board(STABLE_PORT, baud=921600)
    try:
        synchronize(p)
        record["queries"] = queries(p)
        record["setting_replies"] = settings(p, args.frequency, args.bandwidth, args.gain)
        start = time.monotonic_ns()
        record["acquisition_ready_monotonic_ns"] = start
        print("ACQUISITION_READY", flush=True)
        while (time.monotonic_ns() - start) / 1e9 < args.seconds:
            payload, result = capture(p, 16380, 16000000, 8)
            index = len(rows)
            row = {"capture_index": index, **result,
                   "crc_and_count_valid": result["crc_ok"] and result["sample_count_ok"],
                   "private_payload_sha256": hashlib.sha256(payload).hexdigest()}
            path = private / f"iq-{index:04d}.bin"
            path.write_bytes(payload); path.chmod(0o600)
            if row["crc_and_count_valid"]:
                row.update(numerical_stats(payload, 16380, 8))
                iq = unpack(payload, 16380, 8)
                psd = np.abs(np.fft.fftshift(np.fft.fft((iq - iq.mean()) * np.hanning(len(iq))))) ** 2
                freq = np.fft.fftshift(np.fft.fftfreq(len(iq), 1 / 16000000)) + args.frequency * 1e6
                signal = (freq > 2401.5e6) & (freq < 2402.5e6)
                background = ((freq > 2398.5e6) & (freq < 2399.5e6)) | ((freq > 2403.5e6) & (freq < 2404.5e6))
                row["channel_to_background_db"] = float(10 * np.log10((psd[signal].mean() + 1e-20) / (psd[background].mean() + 1e-20)))
            rows.append(row)
            if index % 25 == 0:
                print(f"capture={index} CRC={row['crc_and_count_valid']}", flush=True)
        record["completed"] = True
    finally:
        try: command(p, "RELEASE")
        except Exception: pass
        p.close()
        record["ended_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        record["captures"] = len(rows)
        record["integrity_failures"] = sum(not r["crc_and_count_valid"] for r in rows)
        (args.output / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
        with (args.output / "captures.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=sorted({k for row in rows for k in row}))
            writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    main()
