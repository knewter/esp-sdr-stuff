"""Immutable source exports preserve real Git blobs despite working-tree edits."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/export_sources.py"
spec = importlib.util.spec_from_file_location("export_sources", SCRIPT)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

class CommittedExports(unittest.TestCase):
    def test_batch_reads_committed_text_and_binary_with_spaces(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.DEVNULL)
            git("init")
            expected = {"text with spaces.md": b"committed\n", "image.png": b"\x00\xff\nblob 123\n", "empty.txt": b""}
            for name, payload in expected.items():
                (repo / name).write_bytes(payload)
            git("add", ".")
            git("-c", "user.name=Export fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
            revision = git("rev-parse", "HEAD").decode().strip()
            for name in expected:
                (repo / name).write_bytes(b"uncommitted replacement")
            self.assertEqual(dict(exporter.committed_payloads(repo, revision, sorted(expected))), expected)
            with self.assertRaises(ValueError):
                dict(exporter.committed_payloads(repo, revision, ["missing.md"]))
