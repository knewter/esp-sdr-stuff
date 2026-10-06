#!/usr/bin/env python3
"""Export cited source files from exactly the work snapshot's commit."""
from pathlib import Path
import io
import json
import shutil
import subprocess
ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = (".png", ".svg", ".jpg", ".jpeg", ".gif", ".webp")
def committed_payloads(repo, revision, paths):
    """Read exact committed blobs in one Git process, including binary images."""
    if any("\n" in path or "\r" in path for path in paths):
        raise ValueError("Source paths cannot contain line separators")
    requests = "".join(f"{revision}:{path}\n" for path in paths).encode()
    result = subprocess.run(["git", "cat-file", "--batch"], cwd=repo,
                            input=requests, check=True, capture_output=True)
    stream = io.BytesIO(result.stdout)
    for path in paths:
        header = stream.readline().split()
        if len(header) != 3 or header[1] != b"blob":
            raise ValueError(f"Committed source blob unavailable: {path}")
        size = int(header[2])
        if size < 0:
            raise ValueError(f"Invalid committed blob size: {path}")
        payload = stream.read(size)
        if len(payload) != size or stream.read(1) != b"\n":
            raise ValueError(f"Incomplete committed source blob: {path}")
        yield path, payload
    if stream.read(1):
        raise ValueError("Unexpected committed source output")

def export():
    data = json.loads((ROOT / "site/src/data/work.json").read_text())
    revision = data["sourceRevision"]
    output = ROOT / "site/public/source"
    if output.exists(): shutil.rmtree(output)
    requested = set()
    for item in data["items"]:
        requested.update(item["evidence"])
        requested.update(doc["path"] for doc in item["details"])
    for path in data["trackedPaths"]:
        if path.startswith(("docs/", "openspec/", "scripts/", "tools/", "tests/", ".skills/", "nix/", "firmware/")) or path in ("README.md", "AGENTS.md", "flake.nix", "flake.lock", "Taskfile.yml"):
            requested.add(path)
    known = set(data["trackedPaths"])
    paths = sorted(requested)
    for path in paths:
        if path not in known: raise ValueError(f"Uncommitted source: {path}")
        if path.endswith((".bin", ".avm")) or path.startswith("backups/"):
            raise ValueError(f"Firmware backup cannot be published: {path}")
    # Only images are copied (pages embed them). Every other cited file links
    # to github.com/knewter/esp-sdr-stuff at this revision; the checks above
    # still refuse uncommitted or backup paths.
    images = [path for path in paths if path.lower().endswith(IMAGE_SUFFIXES)]
    for path, payload in committed_payloads(ROOT, revision, images):
        dest = output / revision / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
    (ROOT / "site/public/revision.json").write_text(json.dumps({"revision": revision}) + "\n")
    print(f"checked {len(requested)} committed sources, copied {len(images)} images at {revision[:12]}")
if __name__ == "__main__": export()
