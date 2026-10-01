#!/usr/bin/env python3
"""Bounded receive-only RTL test-mode continuity runs; writes sanitized proof."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import signal
import shutil
import subprocess
import threading
import time


def sanitize(text):
    return re.sub(r"(?i)(SN:\s*)[^\s,]+", r"\1[redacted]", text)


def parse_output(text):
    lost = [int(n) for n in re.findall(r"lost at least (\d+) bytes", text)]
    ppm = re.findall(r"Samples per million lost \(minimum\): (\d+)", text)
    rates = [int(n) for n in re.findall(r"real sample rate: (\d+)", text)]
    return {
        "reported_lost_bytes_lower_bound": sum(lost),
        "loss_reports": len(lost),
        "reported_minimum_loss_per_million": int(ppm[-1]) if ppm else None,
        "sample_rate_observations_hz": rates,
        "cleanup_reported": "User cancel, exiting" in text,
        "async_started": "Reading samples in async mode" in text,
    }


def measure(rate, seconds, folder):
    executable = shutil.which("rtl_test")
    if not executable:
        raise RuntimeError("rtl_test is not installed")
    cmd = ["stdbuf", "-oL", "-eL", executable, "-d", "0", "-s", str(rate), "-p10"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines = queue.Queue()

    def read():
        for line in proc.stdout:
            lines.put((time.monotonic(), sanitize(line)))
        lines.put((time.monotonic(), None))

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    started = time.monotonic()
    streaming = None
    stop = None
    records = []
    try:
        while True:
            try:
                stamp, line = lines.get(timeout=0.1)
                if line is None:
                    break
                records.append(line)
                if "Reading samples in async mode" in line:
                    streaming = stamp
            except queue.Empty:
                pass
            now = time.monotonic()
            if stop is None and streaming is not None and now - streaming >= seconds:
                stop = now
                proc.send_signal(signal.SIGINT)
            if streaming is None and now - started > 15:
                raise RuntimeError("RTL test did not enter asynchronous streaming")
            if stop is not None and now - stop > 10:
                raise RuntimeError("RTL test did not finish after SIGINT")
        returncode = proc.wait(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        reader.join(timeout=2)
        proc.stdout.close()
    output = "".join(records)
    (folder / f"rate-{rate}.log").write_text(output)
    result = {"command": cmd, "requested_rate_hz": rate, "requested_stream_duration_s": seconds,
              "observed_stream_before_sigint_s": None if streaming is None or stop is None else stop-streaming,
              "process_duration_s": time.monotonic()-started, "returncode": returncode,
              **parse_output(output)}
    if returncode != 0 or not result["cleanup_reported"] or not result["async_started"] or stop is None:
        raise RuntimeError(f"Incomplete receiver run: {result}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=65)
    parser.add_argument("--rates", type=int, nargs="+", default=[1024000, 2048000, 2400000, 2560000])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 60 <= args.seconds <= 3600 or any(rate <= 0 for rate in args.rates):
        parser.error("Require finite duration of 60–3600 seconds and positive sample rates")
    args.output.mkdir(parents=True, exist_ok=False)
    result = {
        "captured_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kernel": os.uname().release,
        "tool_sha256": hashlib.sha256(Path(shutil.which("rtl_test")).read_bytes()).hexdigest(),
        "mode": "RTL2832 internal incrementing-byte test pattern, asynchronous, no RF input",
        "loss_semantics": "rtl_test lower-bound discontinuity estimate in bytes; zero is not proof of no modulo-256 losses",
        "runs": [],
    }
    try:
        for rate in args.rates:
            measured = measure(rate, args.seconds, args.output)
            result["runs"].append(measured)
            print(json.dumps(measured), flush=True)
            (args.output / "capture.json").write_text(json.dumps(result, indent=2)+"\n")
    finally:
        (args.output / "capture.json").write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()
