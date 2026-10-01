#!/usr/bin/env python3
"""Export cited source files from exactly the work snapshot's commit."""
from pathlib import Path
import json
import shutil
import subprocess
ROOT = Path(__file__).resolve().parents[1]
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
        if path.startswith(("docs/", "openspec/", "scripts/", "tools/", ".skills/")) or path in ("README.md", "AGENTS.md"):
            requested.add(path)
    known = set(data["trackedPaths"])
    for path in sorted(requested):
        if path not in known: raise ValueError(f"Uncommitted source: {path}")
        if path.endswith((".bin", ".avm")) or path.startswith("backups/"):
            raise ValueError(f"Firmware backup cannot be published: {path}")
        payload = subprocess.run(["git", "show", f"{revision}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout
        dest = output / revision / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
    (ROOT / "site/public/revision.json").write_text(json.dumps({"revision": revision}) + "\n")
    print(f"exported {len(requested)} committed sources at {revision[:12]}")
if __name__ == "__main__": export()
