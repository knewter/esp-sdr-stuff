"""Check built internal URLs, base prefix and proposal/ledger counts."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import os
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "site/dist"

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("href", "src", "poster") and value:
                self.urls.append(value)

class SiteOutput(unittest.TestCase):
    def test_internal_urls_exist(self):
        prefix = os.environ.get("ASTRO_BASE", "/").rstrip("/")
        checked = 0
        for page in DIST.rglob("*.html"):
            parser = Links()
            parser.feed(page.read_text())
            for value in parser.urls:
                parsed = urlsplit(value)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                path = unquote(parsed.path)
                if path.startswith("/"):
                    self.assertTrue(path == prefix or path.startswith(prefix + "/"), (page, value))
                    target = DIST / path[len(prefix):].lstrip("/")
                else:
                    target = page.parent / path
                if target.is_dir():
                    target /= "index.html"
                self.assertTrue(target.is_file(), (page.relative_to(DIST), value))
                checked += 1
        self.assertGreater(checked, 100)

    def test_snapshot_is_consistent(self):
        work = json.loads((ROOT / "site/src/data/work.json").read_text())
        specs = json.loads((ROOT / "site/src/data/specs.json").read_text())
        revision = json.loads((DIST / "revision.json").read_text())
        self.assertEqual(work["sourceRevision"], revision["revision"])
        self.assertEqual(specs["sourceRevision"], revision["revision"])
        self.assertEqual(len(work["items"]), 7)
        self.assertEqual(specs["total"], 3)
        self.assertEqual(specs["tally"]["grounded"], 3)

    def test_no_firmware_backup_is_published(self):
        self.assertFalse(list(DIST.rglob("*.bin")))
        self.assertFalse(list(DIST.rglob("*.avm")))
        self.assertTrue((DIST / "work/index.html").is_file())

if __name__ == "__main__":
    unittest.main()
