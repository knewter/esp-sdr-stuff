#!/usr/bin/env python3
"""Generate data, build Astro, then check links, counts and size/time budgets."""
from pathlib import Path
import argparse
import os
import posixpath
import re
import subprocess
import sys
import time
from html.parser import HTMLParser
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parents[1]
def run(*args): subprocess.run(args, cwd=ROOT, check=True)

def compact_page_urls(page, dist, prefix):
    """Shorten actual URL attributes while preserving their resolved targets.

    Parse tags rather than searching document text: displayed source, scripts
    and preformatted evidence must remain byte-for-byte presentation text.
    Keep the original quote style and every query, fragment and trailing slash.
    """
    text = page.read_bytes().decode("utf-8")
    offsets = [0, *(match.end() for match in re.finditer("\n", text))]
    directory = prefix + "/" + page.parent.relative_to(dist).as_posix().removeprefix(".")
    changes = []
    attribute = re.compile(r'''([^\s/<>=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?''')
    class Tags(HTMLParser):
        def handle_starttag(self, tag, attrs):
            token = self.get_starttag_text()
            line, column = self.getpos()
            start = offsets[line - 1] + column
            attribute_start = 1 + len(tag)
            for match in attribute.finditer(token[attribute_start:]):
                if match.group(1).lower() not in ("href", "src", "poster"):
                    continue
                group = next((n for n in (2, 3, 4) if match.group(n) is not None), None)
                if group is None:
                    continue
                value = match.group(group)
                if not value.startswith(prefix + "/") or value.startswith("//"):
                    continue
                url = urlsplit(value)
                if "//" in url.path:
                    continue
                relative = posixpath.relpath(url.path, start=directory)
                if url.path.endswith("/"):
                    relative = "./" if relative == "." else relative + "/"
                if ":" in relative.split("/", 1)[0]:
                    relative = "./" + relative
                shorter = relative + value[len(url.path):]
                if len(shorter) >= len(value) or re.search(r'''[\s"'`=<>]''', shorter):
                    continue
                changes.append((start + attribute_start + match.start(group),
                                start + attribute_start + match.end(group), shorter))
        handle_startendtag = handle_starttag
    Tags().feed(text)
    for start, end, value in reversed(changes):
        text = text[:start] + value + text[end:]
    page.write_bytes(text.encode("utf-8"))
    return len(changes)

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
    prefix = env.get("ASTRO_BASE", "/").rstrip("/")
    for page in pages:
        compact_page_urls(page, dist, prefix)
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
