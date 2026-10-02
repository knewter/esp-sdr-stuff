#!/usr/bin/env python3
"""Load the flake's picotool image and invoke identity-targeted preservation."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    # Help must remain free of Docker and hardware operations.
    if not sys.argv[1:] or any(arg in ("--help", "-h") for arg in sys.argv[1:]):
        return subprocess.run([sys.executable, str(ROOT / "tools/preserve_forgix.py"), "--help"]).returncode
    if any(arg == "--container-image" or arg.startswith("--container-image=") for arg in sys.argv[1:]):
        raise SystemExit("This task selects the immutable Nix image; use forgix:preserve for an explicit image")
    archive = os.environ.get("PICOTOOL_USB_IMAGE")
    tag = os.environ.get("PICOTOOL_USB_IMAGE_TAG")
    if not archive or not tag or not Path(archive).is_file() or not archive.startswith("/nix/store/"):
        raise SystemExit("Enter nix develop to obtain the pinned picotool container image")
    subprocess.run(["docker", "load", "--input", archive], stdout=sys.stderr, check=True)
    images = json.loads(subprocess.check_output(["docker", "image", "inspect", tag], text=True))
    if len(images) != 1 or not images[0]["Id"].startswith("sha256:"):
        raise SystemExit("Cannot resolve the loaded image to one immutable ID")
    return subprocess.run([
        sys.executable, str(ROOT / "tools/preserve_forgix.py"),
        "--usb-container", "--container-image", images[0]["Id"], *sys.argv[1:],
    ]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
