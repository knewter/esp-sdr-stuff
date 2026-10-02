#!/usr/bin/env python3
"""Start an owned preview, wait for readiness, run browser checks, and stop it."""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4321)
    parser.add_argument("--output", default="test-results/browser")
    args = parser.parse_args()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))
    prefix = os.environ.get("ASTRO_BASE", "/").strip("/")
    base = f"http://127.0.0.1:{args.port}/" + (prefix + "/" if prefix else "")
    expected_revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
    ).strip()
    if json.loads((ROOT / "site/dist/revision.json").read_text()).get("revision") != expected_revision:
        raise SystemExit("Rebuild the committed site before checking its browser")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "preview.log").open("w") as log:
        preview = subprocess.Popen(
            ["npm", "run", "preview", "--prefix", "site", "--", "--host", "127.0.0.1", "--port", str(args.port), "--strictPort"],
            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 45
            while True:
                if preview.poll() is not None:
                    raise RuntimeError(f"Preview exited early; inspect {output / 'preview.log'}")
                try:
                    with urlopen(base + "revision.json", timeout=1) as response:
                        revision = json.load(response).get("revision")
                        # Vite logs its bound URL only after starting the owned server.
                        owned_ready = base in (output / "preview.log").read_text()
                        if response.status == 200 and revision == expected_revision and owned_ready and preview.poll() is None:
                            break
                except (URLError, TimeoutError, ValueError):
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Preview did not become ready; inspect {output / 'preview.log'}")
                time.sleep(0.2)
            subprocess.run(
                [sys.executable, "tests/site_browser.py", "--url", base, "--output", str(output)],
                cwd=ROOT, check=True,
            )
        finally:
            try:
                os.killpg(preview.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                preview.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(preview.pid, signal.SIGKILL)
                preview.wait()


if __name__ == "__main__":
    main()
