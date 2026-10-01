#!/usr/bin/env python3
"""Bounded passive FM-band discovery sweep; antenna/source remain unverified."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import signal
import subprocess
import time
from measure_rtl_continuity import sanitize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    executable = shutil.which("rtl_power")
    if not executable:
        parser.error("rtl_power is not installed")
    args.output.mkdir(parents=True, exist_ok=False)
    cmd = [executable, "-d", "0", "-f", "88M:108M:10k", "-g", "19.7", "-c", "0.2",
           "-i", "2", "-e", "20s", str(args.output / "fm-sweep.csv")]
    start = time.monotonic()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    forced_stop = False
    try:
        output, _ = proc.communicate(timeout=35)
    except subprocess.TimeoutExpired:
        forced_stop = True
        proc.send_signal(signal.SIGINT)
        try:
            output, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    (args.output / "receiver.log").write_text(sanitize(output))
    metadata = {
        "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "command": cmd,
        "process_duration_s": time.monotonic()-start, "returncode": proc.returncode,
        "tool_sha256": hashlib.sha256(Path(executable).read_bytes()).hexdigest(), "forced_stop": forced_stop,
        "receiver": "RTLSDRBlog Blog V4 / R828D", "gain_requested_db": 19.7, "bias_tee": "not enabled",
        "antenna": "attachment and type unverified", "source": "uncontrolled ambient public FM band; station identity unverified",
        "power_units": "uncalibrated rtl_power output, not defensible dBm",
        "scope": "sequential hopping survey, not simultaneous continuous 20 MHz IQ",
    }
    (args.output / "capture.json").write_text(json.dumps(metadata, indent=2)+"\n")
    print(json.dumps(metadata, indent=2))
    if proc.returncode != 0 or forced_stop:
        raise SystemExit("Receiver survey failed or required forced stopping; inspect retained logs")


if __name__ == "__main__":
    main()
