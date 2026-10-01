#!/usr/bin/env python3
"""Record identity and boot output without writing flash; resets the board."""
import argparse
import datetime
import json
from pathlib import Path
import re
import subprocess
import time
import serial

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--port", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = subprocess.run(["esptool", "--port", args.port, "--no-stub", "--connect-attempts", "2", "flash-id"],
                        capture_output=True, text=True, timeout=25)
identity = re.sub(r"MAC:\s*[0-9a-f:]+", "MAC: [redacted device address]", result.stdout, flags=re.I)
(args.output / "chip-and-flash.log").write_text(identity + result.stderr)
if result.returncode:
    raise SystemExit(result.returncode)
connection = serial.Serial(port=None, baudrate=115200, timeout=0.1, exclusive=True)
connection.dtr = False
connection.rts = False
connection.port = args.port
connection.open()
data = bytearray()
try:
    until = time.monotonic() + 4
    while time.monotonic() < until:
        data.extend(connection.read(8192))
finally:
    connection.close()
(args.output / "boot.log").write_text(re.sub(r"\x1b\[[0-9;]*m", "", data.decode(errors="replace")))
(args.output / "capture.json").write_text(json.dumps({
    "started_utc": started, "port": args.port, "baud": 115200,
    "identity_command": "esptool --port SELECTED_PORT --no-stub --connect-attempts 2 flash-id",
    "class": "Board capture", "firmware_written": False,
    "reset": "Bootloader query resets the board; opening the UART may also reset it.",
    "redactions": ["device MAC address"], "boot_bytes": len(data),
}, indent=2) + "\n")
print(identity)
print(f"Boot recorded: {len(data)} bytes; port closed; no flash writes.")
