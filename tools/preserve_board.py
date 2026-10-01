#!/usr/bin/env python3
"""Read and independently reread all ESP32 flash; publish only sanitized proof."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import time

SIZE = 0x400000

def clean(value):
    return re.sub(r"(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", "[redacted device address]", value)

def partitions(image):
    entries = []
    table = image[0x8000:0x9000]
    for start in range(0, len(table), 32):
        row = table[start:start + 32]
        magic = struct.unpack_from("<H", row)[0]
        if magic == 0xEBEB:
            if hashlib.md5(table[:start]).digest() != row[16:32]:
                raise ValueError("Partition table checksum mismatch")
            break
        if magic == 0xFFFF:
            break
        if magic != 0x50AA:
            raise ValueError(f"Unexpected partition magic at entry {start // 32}")
        _, kind, subtype, offset, size, label, flags = struct.unpack("<HBBII16sI", row)
        if offset + size > len(image):
            raise ValueError("Partition exceeds physical flash")
        entries.append({"type": kind, "subtype": subtype, "offset": offset,
                        "size": size, "label": label.rstrip(b"\0").decode(), "flags": flags})
    if not entries:
        raise ValueError("No standard ESP-IDF partition entries found")
    for previous, following in zip(sorted(entries, key=lambda p: p["offset"]), sorted(entries, key=lambda p: p["offset"])[1:]):
        if previous["offset"] + previous["size"] > following["offset"]:
            raise ValueError("Overlapping partitions")
    return entries

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--private-dir", type=Path, default=Path("backups"))
    parser.add_argument("--evidence", type=Path, default=Path("docs/evidence/firmware-preservation"))
    args = parser.parse_args()
    if "Silicon_Labs_CP2102" not in args.port:
        raise SystemExit("Select the confirmed stable CP2102 identity")
    args.private_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.evidence.mkdir(parents=True, exist_ok=True)
    if (args.private_dir / "original.bin").exists():
        raise SystemExit("Existing baseline retained; refusing to overwrite original.bin")
    occupied = subprocess.run(["fuser", args.port], capture_output=True)
    if occupied.returncode == 0:
        raise SystemExit("Device is already open")
    started = datetime.now(timezone.utc).isoformat()
    commands = []
    def run(command, filename, timeout):
        before = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        log = clean(result.stdout + result.stderr)
        (args.evidence / filename).write_text(log)
        commands.append({"command": ["SELECTED_PORT" if x == args.port else x for x in command],
                         "exit_code": result.returncode, "seconds": time.monotonic() - before, "log": filename})
        if result.returncode:
            raise RuntimeError(f"{filename} failed, see sanitized log")
        print(filename, "passed", flush=True)
        return log
    run(["espefuse", "--chip", "esp32", "--port", args.port, "summary",
         "ABS_DONE_0", "ABS_DONE_1", "FLASH_CRYPT_CNT", "DISABLE_DL_ENCRYPT", "DISABLE_DL_DECRYPT", "DISABLE_DL_CACHE"],
        "security.log", 40)
    hashes = []
    for index, name in enumerate(("original.bin", "readback.bin"), 1):
        dest = args.private_dir / name
        run(["esptool", "--chip", "esp32", "--port", args.port, "--baud", "460800",
             "read-flash", "--no-progress", "0", hex(SIZE), str(dest)], f"read-{index}.log", 600)
        dest.chmod(0o600)
        payload = dest.read_bytes()
        if len(payload) != SIZE:
            raise RuntimeError("Incomplete flash backup")
        hashes.append(hashlib.sha256(payload).hexdigest())
    if hashes[0] != hashes[1]:
        raise RuntimeError("Independent flash reads differ")
    manifest = {"started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
                "class": "Physical board flash read", "bytes": SIZE, "sha256": hashes[0],
                "independent_reads": 2, "read_hashes_equal": True, "firmware_written": False,
                "partitions": partitions(payload), "commands": commands,
                "restoration_proven": False}
    (args.evidence / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Preserved {SIZE} bytes; independent reads match SHA-256 {hashes[0]}")

if __name__ == "__main__":
    main()
