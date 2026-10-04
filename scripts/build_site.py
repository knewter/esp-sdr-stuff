#!/usr/bin/env python3
"""Generate data, build Astro, then check links, counts and size/time budgets."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
def run(*args): subprocess.run(args, cwd=ROOT, check=True)
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", "openspec", "docs"], cwd=ROOT, text=True, capture_output=True, check=True).stdout
    if dirty:
        print("Commit scoped OpenSpec/evidence before building:\n" + dirty, file=sys.stderr)
        return 2
    run("node", "tests/test_work_markdown_links.mjs")
    run(sys.executable, "scripts/render_work_board.py")
    run(sys.executable, "scripts/export_sources.py")
    run(sys.executable, "scripts/render_specs.py")
    env = {**os.environ, "CI": "1"}
    if args.local: env.pop("ASTRO_BASE", None)
    subprocess.run(["npm", "run", "build", "--prefix", "site"], cwd=ROOT, env=env, check=True)
    # Compact generated pages while retaining all immutable source/evidence
    # bytes. Compact formatting whitespace and optional end tags while keeping
    # explicit document tags and default attributes. Preformatted text remains
    # intact; the browser checks cover the rendered UI.
    minifier = Path(os.environ["MINIFY_EXECUTABLE"]).resolve(strict=True)
    if not minifier.is_relative_to("/nix/store"):
        raise RuntimeError("Locked Nix HTML minifier required")
    dist = ROOT / "site/dist"
    pages = sorted(p for p in dist.rglob("*.html") if not p.is_relative_to(dist / "source"))
    run(str(minifier), "--type=html", "--inplace", "--html-keep-document-tags",
        "--html-keep-default-attrvals",
        "--js-keep-var-names", "--json-keep-numbers", *map(str, pages))
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_site_output.py")
    files = [p for p in dist.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    # The growing, byte-exact source archive is most of the publication. Bound
    # generated UI separately so more retained evidence cannot hide page bloat.
    page_size = sum(p.stat().st_size for p in files if not p.is_relative_to(dist / "source"))
    elapsed = time.monotonic() - started
    if size > 24 * 1024 * 1024 or page_size > 2 * 1024 * 1024 or elapsed > 120:
        raise RuntimeError(f"Site exceeds budget: {size} total bytes, {page_size} page bytes, {elapsed:.2f} seconds")
    print(f"Site verified: {size:,} bytes ({page_size:,} outside source archive) in {elapsed:.2f}s")
    return 0
if __name__ == "__main__": raise SystemExit(main())
