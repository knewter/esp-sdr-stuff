"""Focused native Node conservation checks, included by existing task test."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkEvidenceMenus(unittest.TestCase):
    def test_native_toggle_cloning_and_fallback_boundaries(self):
        subprocess.run(["node", str(ROOT / "tests/test_work_evidence_menus.mjs")],
                       cwd=ROOT, check=True, timeout=20)

if __name__ == '__main__':
    unittest.main()
