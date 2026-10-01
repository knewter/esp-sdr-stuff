"""Verify that receiver evidence parsing does not invent continuity success."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools/measure_rtl_continuity.py"
spec = importlib.util.spec_from_file_location("rtl_continuity", MODULE)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class ReceiverEvidenceParsing(unittest.TestCase):
    def test_missing_summary_is_unknown_not_zero(self):
        self.assertIsNone(tool.parse_output("Reading samples in async mode...\n")["reported_minimum_loss_per_million"])

    def test_discontinuities_are_bytes_not_complex_samples(self):
        parsed = tool.parse_output("lost at least 256 bytes\nlost at least 19 bytes\n"
                                   "Samples per million lost (minimum): 5\n"
                                   "real sample rate: 2047990 current PPM: -5 cumulative PPM: -5\n"
                                   "User cancel, exiting...\n")
        self.assertEqual(parsed["reported_lost_bytes_lower_bound"], 275)
        self.assertEqual(parsed["loss_reports"], 2)
        self.assertEqual(parsed["sample_rate_observations_hz"], [2047990])
        self.assertTrue(parsed["cleanup_reported"])
        self.assertFalse(parsed["async_started"])

    def test_identity_redaction_keeps_receiver_model(self):
        original = "0: RTLSDRBlog, Blog V4, SN: ABC123\nUsing device 0: Generic RTL2832U OEM\n"
        sanitized = tool.sanitize(original)
        self.assertNotIn("ABC123", sanitized)
        self.assertIn("Blog V4", sanitized)
        self.assertIn("SN: [redacted]", sanitized)


if __name__ == "__main__":
    unittest.main()
