#!/usr/bin/env python3
"""Bounded receive-only RDS trial, with private MPX and public decoder evidence."""
import argparse
from collections import Counter
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal as os_signal
import subprocess
import time

import numpy as np
import scipy
from scipy import signal
from scipy.io import wavfile
from measure_rtl_continuity import sanitize


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def summarize(lines):
    records = [json.loads(line) for line in lines.splitlines() if line.strip()]
    times = [r["time_from_start"] for r in records if "time_from_start" in r]
    complete = valid = missing = 0
    direct_pi = Counter()
    for record in records:
        blocks = record["raw_data"].split()
        if len(blocks) != 4:
            raise ValueError("Expected four redsea raw blocks")
        for block in blocks:
            if block != "----" and (len(block) != 4 or any(c not in "0123456789ABCDEF" for c in block)):
                raise ValueError("Unexpected redsea raw block")
        valid += sum(block != "----" for block in blocks)
        missing += blocks.count("----")
        complete += "----" not in blocks
        if blocks[0] != "----":
            direct_pi["0x" + blocks[0]] += 1
    return {
        "emitted_groups": len(records), "complete_four_block_groups": complete,
        "valid_blocks_in_emitted_groups": valid, "missing_blocks_in_emitted_groups": missing,
        "direct_valid_block_a_pi_counts": dict(direct_pi),
        "callsigns_in_decoder_output": sorted({r["callsign"] for r in records if "callsign" in r}),
        "ps_values": sorted({r["ps"] for r in records if "ps" in r}),
        "radiotext_values": sorted({r["radiotext"] for r in records if "radiotext" in r}),
        "first_group_time_s": min(times) if times else None,
        "last_group_time_s": max(times) if times else None,
        "count_scope": "Emitted groups only; unsynchronized/omitted groups excluded. PI field can be inherited; direct PI counts use raw block A only.",
        "checkword_policy": "redsea --no-fec; no burst correction; valid blocks have expected syndrome/offset. This is RDS 10-bit checkword evidence, not a separate external CRC verifier.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--iq", type=Path)
    source.add_argument("--capture-seconds", type=float)
    parser.add_argument("--redsea", required=True, type=Path)
    parser.add_argument("--private-mpx", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--name", required=True, choices=["retained", "live"])
    parser.add_argument("--center-hz", type=int, default=101000000)
    parser.add_argument("--channel-hz", type=int, default=101100000)
    parser.add_argument("--iq-rate", type=int, default=1024000)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.private_mpx.exists():
        parser.error("Private MPX already exists; choose a new path")
    meta = {"recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "antenna": "Exact model, attachment and orientation unverified; no physical intervention",
            "bias_tee": "not enabled", "channel_hz": args.channel_hz,
            "numpy": np.__version__, "scipy": scipy.__version__}
    if args.iq:
        rate = args.iq_rate
        if rate != 1024000:
            parser.error("This IQ path requires 1.024 MS/s for fixed decimation")
        raw = np.fromfile(args.iq, dtype=np.uint8)
        if len(raw) % 2 or len(raw) < 2 * rate:
            parser.error("IQ must contain whole pairs and at least one second")
        iq = (raw[::2].astype(np.float32)-127.5)/128 + 1j*(raw[1::2].astype(np.float32)-127.5)/128
        iq *= np.exp(-2j*np.pi*(args.channel_hz-args.center_hz)/rate*np.arange(len(iq)))
        channel = signal.resample_poly(iq, 1, 4, window=signal.firwin(255, 90000, fs=rate))
        mpx_rate = rate // 4
        mpx = np.angle(channel[1:]*np.conjugate(channel[:-1]))*mpx_rate/(2*np.pi)
        mpx = mpx[int(.1*mpx_rate):]
        peak = float(np.max(abs(mpx)))
        if peak == 0:
            parser.error("Empty modulation")
        wavfile.write(args.private_mpx, mpx_rate, np.rint(mpx/peak*30000).astype(np.int16))
        meta.update({"input_iq_sha256": digest(args.iq), "iq_pairs": len(iq),
                     "iq_rate_hz": rate, "nominal_iq_duration_s": len(iq)/rate,
                     "center_hz": args.center_hz, "mpx_rate_hz": mpx_rate,
                     "mpx_samples": len(mpx), "pcm_peak_scale_hz": peak,
                     "demodulator": "Mix channel offset; 255-tap 90 kHz lowpass; decimate4; quadrature phase difference; discard100ms; peak normalize to30000 PCM"})
        decode_cmd = [str(args.redsea.resolve()), "-f", str(args.private_mpx)]
    else:
        if not 1 <= args.capture_seconds <= 60:
            parser.error("Capture duration must be 1..60 seconds")
        mpx_rate = 171000
        executable = os.environ.get("RTL_FM") or shutil.which("rtl_fm")
        if not executable:
            parser.error("rtl_fm is missing; enter the Nix development shell")
        cmd = [executable, "-d", "0", "-M", "fm", "-l", "0", "-A", "std", "-p", "0",
               "-s", str(mpx_rate), "-g", "19.7", "-F", "9", "-f", str(args.channel_hz)]
        start = time.monotonic()
        forced_kill = False
        with args.private_mpx.open("xb") as sink:
            proc = subprocess.Popen(cmd, stdout=sink, stderr=subprocess.PIPE)
            try:
                try:
                    _, log = proc.communicate(timeout=args.capture_seconds)
                except subprocess.TimeoutExpired:
                    proc.send_signal(os_signal.SIGINT)
                    try:
                        _, log = proc.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        forced_kill = True
                        proc.kill()
                        _, log = proc.communicate()
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
        (args.output / (args.name + "-receiver.log")).write_text(sanitize(log.decode(errors="replace")))
        meta.update({"receiver_command": cmd, "receiver_returncode": proc.returncode,
                     "process_duration_s": time.monotonic()-start, "capture_limit_s": args.capture_seconds,
                     "forced_kill": forced_kill, "rtl_fm_sha256": digest(cmd[0]),
                     "mpx_rate_requested_hz": mpx_rate, "mpx_samples": args.private_mpx.stat().st_size//2,
                     "nominal_mpx_duration_s": args.private_mpx.stat().st_size/(2*mpx_rate),
                     "gain_requested_db": 19.7})
        if proc.returncode != 0 or forced_kill or args.private_mpx.stat().st_size % 2:
            (args.output / (args.name + "-trial.json")).write_text(json.dumps(meta, indent=2)+"\n")
            raise SystemExit("Receiver failed; inspect retained evidence")
        decode_cmd = [str(args.redsea.resolve()), "--input", "mpx", "-r", str(mpx_rate)]
    meta.update({"mpx_sha256": digest(args.private_mpx), "mpx_bytes": args.private_mpx.stat().st_size,
                 "redsea_sha256": digest(args.redsea), "raw_publication": "IQ/MPX kept private in ignored scratch; decoded public broadcast metadata only"})
    decode_cmd += ["--no-fec", "--show-raw", "--rbds", "--bler", "--time-from-start"]
    with args.private_mpx.open("rb") as data:
        decoded = subprocess.run(decode_cmd, stdin=data, capture_output=True, text=True, timeout=120)
    meta["decoder_command"] = decode_cmd
    meta["decoder_returncode"] = decoded.returncode
    (args.output / (args.name + "-decoder.ndjson")).write_text(decoded.stdout)
    (args.output / (args.name + "-decoder.log")).write_text(decoded.stderr)
    if decoded.returncode != 0:
        raise SystemExit("Decoder failed")
    meta["decode_summary"] = summarize(decoded.stdout)
    (args.output / (args.name + "-trial.json")).write_text(json.dumps(meta, indent=2)+"\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
