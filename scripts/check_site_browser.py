#!/usr/bin/env python3
"""Start an owned preview, wait for readiness, run browser checks, and stop it."""
import argparse
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import time
import threading
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4321)
    parser.add_argument("--output", default="test-results/browser")
    args = parser.parse_args()
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
        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, format, *values):
                log.write((format % values) + "\n")
                log.flush()

            def do_GET(self):
                if prefix:
                    route = "/" + prefix + "/"
                    if not self.path.startswith(route):
                        self.send_error(404)
                        return
                    self.path = self.path[len(route) - 1:]
                return super().do_GET()

        # Bind before starting the thread: another listener cannot win a
        # probe/release/start race. Serve the same static bytes Pages publishes.
        preview = ThreadingHTTPServer(("127.0.0.1", args.port),
            partial(Handler, directory=str(ROOT / "site/dist")))
        thread = threading.Thread(target=preview.serve_forever, daemon=True)
        thread.start()
        log.write(f"Owned static preview: {base}\n")
        log.flush()
        try:
            deadline = time.monotonic() + 45
            while True:
                if not thread.is_alive():
                    raise RuntimeError(f"Preview exited early; inspect {output / 'preview.log'}")
                try:
                    with urlopen(base + "revision.json", timeout=1) as response:
                        revision = json.load(response).get("revision")
                        if response.status == 200 and revision == expected_revision and thread.is_alive():
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
            preview.shutdown()
            preview.server_close()
            thread.join(timeout=5)
            if thread.is_alive():
                raise RuntimeError("Owned static preview thread did not stop")


if __name__ == "__main__":
    main()
