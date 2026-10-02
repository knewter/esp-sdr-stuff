"""Fail-closed gateware planning checks; no hardware or vendor tools invoked."""
from contextlib import redirect_stderr
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import forgix_toolchain_check as tool


class ToolchainTests(unittest.TestCase):
    def test_unknown_physical_parameters_never_adopt_upstream_defaults(self):
        for values in [(None, None, None, False), ("T8F49C2", 32000000, "rev A", False),
                       ("T8F49I2", 32000000, "unknown", True),
                       ("T8F49I2", 32000000, "   ", True),
                       ("T8F49I2", 0, "rev A", True), ("T8F81C2", 32000000, "rev A", True)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                tool.parameters(*values)
        actual = tool.parameters("T8F49I2", 24000000, "rev A", True)
        self.assertEqual(actual["clock_hz"], 24000000)
        self.assertEqual(actual["device"], "T8F49I2")

    def test_plan_without_physical_parameters_fails_before_commands(self):
        with patch.object(tool, "command_check") as command:
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                tool.main(["--plan"])
            self.assertEqual(error.exception.code, 2)
            command.assert_not_called()

    def test_vendor_presence_requires_setup_and_compile_script(self):
        self.assertIsNone(tool.vendor_layout(None))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bin").mkdir()
            (root / "bin/setup.sh").write_text("# existing installation\n")
            with self.assertRaises(ValueError):
                tool.vendor_layout(directory)
            (root / "scripts").mkdir()
            (root / "scripts/efx_run.py").write_text("# existing CLI\n")
            self.assertEqual(tool.vendor_layout(directory), root)

    def test_compile_is_refused_without_vendor_or_runtime_before_imports(self):
        selected = tool.parameters("T8F49I2", 32000000, "rev A", True)
        with self.assertRaises(ValueError):
            tool.gateware_build(selected, Path("unused"), None)
        with patch.dict(tool.os.environ, {"FORGIX_INSIDE_EFINITY": ""}):
            with self.assertRaises(ValueError):
                tool.gateware_build(selected, Path("unused"), Path("vendor"))


if __name__ == "__main__":
    unittest.main()
