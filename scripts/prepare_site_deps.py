#!/usr/bin/env python3
"""Make the flake's locked Node dependencies writable for Astro's build cache."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    source_env = os.environ.get("SITE_NODE_MODULES")
    if not source_env:
        raise SystemExit("Enter the locked environment: nix develop --command task site:deps")
    source = Path(source_env).resolve()
    if not source.is_dir() or not str(source).startswith("/nix/store/"):
        raise SystemExit("SITE_NODE_MODULES must name the flake's Nix dependency directory")
    destination = ROOT / "site/node_modules"
    marker = destination / ".esp-sdr-nix-deps.json"
    expected = {
        "source": str(source),
        "package_lock_sha256": hashlib.sha256((ROOT / "site/package-lock.json").read_bytes()).hexdigest(),
    }
    locked_manifest = source.parent / "package-lock.json"
    if not locked_manifest.is_file() or hashlib.sha256(locked_manifest.read_bytes()).hexdigest() != expected["package_lock_sha256"]:
        raise SystemExit("The lockfile changed; re-enter nix develop to rebuild its locked dependencies")
    if marker.is_file() and json.loads(marker.read_text()) == expected:
        print("Locked site dependencies already prepared")
        return
    with tempfile.TemporaryDirectory(prefix=".nix-deps-", dir=ROOT / "site") as staging:
        copied = Path(staging) / "node_modules"
        shutil.copytree(source, copied, symlinks=True)
        for path in [copied, *copied.rglob("*")]:
            if not path.is_symlink():
                path.chmod(path.stat().st_mode | (0o700 if path.is_dir() else 0o200))
        (copied / marker.name).write_text(json.dumps(expected, indent=2) + "\n")
        if destination.is_symlink():
            destination.unlink()
        elif destination.exists():
            shutil.rmtree(destination)
        copied.rename(destination)
    print("Prepared site dependencies from the locked Nix package")


if __name__ == "__main__":
    main()
