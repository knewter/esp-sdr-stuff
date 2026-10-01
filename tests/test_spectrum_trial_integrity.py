"""Independent fake-wire regressions; these do not establish RF reception."""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import esp_sdr_spectrum_bridge as bridge


class Wire:
    def __init__(self, data):
        self.data = bytearray(data)
        self.closed = False

    def read(self, count):
        count = min(count, 7, len(self.data))
        chunk = bytes(self.data[:count])
        del self.data[:count]
        return chunk

    def read_until(self, delimiter, limit):
        result = bytearray()
        while len(result) < limit:
            byte = self.read(1)
            if not byte:
                break
            result.extend(byte)
            if result.endswith(delimiter):
                break
        return bytes(result)

    def close(self):
        self.closed = True


def fft_frame(sequence, sample_index, pairs=256, flags=8):
    raw = bytearray(28 + 256)
    raw[:4] = b"SPC1"
    raw[4:8] = sequence.to_bytes(4, "little")
    raw[8:16] = sample_index.to_bytes(8, "little")
    raw[16:20] = pairs.to_bytes(4, "little")
    raw[20:22] = (1).to_bytes(2, "little")
    raw[22] = flags
    raw[26] = 8
    raw[27] = 2
    raw += zlib.crc32(raw).to_bytes(4, "little")
    return raw


class SpectrumTrialIntegrity(unittest.TestCase):
    def trial(self, frames=None, report=None):
        if frames is None:
            frames = [fft_frame(0, 0), fft_frame(1, 80_000_000)]
        if report is None:
            report = [0, 0, 2, 512, 60_000_000, 0, 0, 2, 0, 0, 2, 0]
        wire = Wire(b"".join(frames) + ("SPECEND " + " ".join(map(str, report)) + "\n").encode())
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            args = SimpleNamespace(output=root / "evidence", private=root / "private", port="MOCK",
                                   baud=2_000_000, frequency=2412, bandwidth=20, gain="hardware",
                                   seconds=60, rate=80_000_000, bins=256)
            stack.enter_context(patch.object(bridge, "open_board", return_value=wire))
            stack.enter_context(patch.object(bridge, "synchronize"))
            stack.enter_context(patch.object(bridge, "queries", return_value={"mock": True}))
            stack.enter_context(patch.object(bridge, "settings", return_value={"mock": True}))
            stack.enter_context(patch.object(bridge, "command", side_effect=lambda port, request:
                                             "SPEC 256 80000000 256 2412" if request.startswith("SPEC ") else "OK"))
            tick = iter(range(0, 1000, 30))
            stack.enter_context(patch.object(bridge.time, "monotonic", side_effect=lambda: next(tick)))
            stack.enter_context(redirect_stdout(io.StringIO()))
            bridge.Trial(args).run()
            result = json.loads((args.output / "results.json").read_text())
        self.assertTrue(wire.closed, "UART must be released on successful and failed trials")
        return result

    def test_consistent_crc_sequences_totals_and_durations_are_accepted(self):
        result = self.trial()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["frames"], 2)
        self.assertEqual(result["nominal_sampled_seconds"], 512 / 80_000_000)

    def test_sequence_gap_is_a_failure_even_with_valid_crc(self):
        result = self.trial([fft_frame(0, 0), fft_frame(2, 80_000_000)])
        self.assertEqual(result["status"], "failed")
        self.assertIn("sequence", result["error"])

    def test_end_report_cannot_mask_a_lost_frame(self):
        result = self.trial(report=[0, 0, 3, 768, 60_000_000, 0, 0, 3, 0, 0, 3, 0])
        self.assertEqual(result["status"], "failed")
        self.assertIn("totals", result["error"])

    def test_early_hardware_stop_is_a_failure(self):
        result = self.trial(report=[0, 0, 2, 512, 60_000_000, 0, 0, 2, 0, 0, 2, 1])
        self.assertEqual(result["status"], "failed")

    def test_short_firmware_duration_is_rejected_despite_host_delay(self):
        result = self.trial(report=[0, 0, 2, 512, 1_000_000, 0, 0, 2, 0, 0, 2, 0])
        self.assertEqual(result["status"], "failed")
        self.assertIn("duration", result["error"])

    def test_invalid_processed_sample_count_cannot_inflate_coverage(self):
        result = self.trial([fft_frame(0, 0, pairs=16380)])
        self.assertEqual(result["status"], "failed")

    def test_missing_snapshot_gap_flag_is_rejected(self):
        result = self.trial([fft_frame(0, 0, flags=0)])
        self.assertEqual(result["status"], "failed")

    def test_crc_corruption_is_a_failure(self):
        raw = fft_frame(0, 0)
        raw[40] ^= 1
        result = self.trial([raw])
        self.assertEqual(result["status"], "failed")
        self.assertIn("CRC", result["error"])

    def test_nonzero_firmware_status_is_a_failure(self):
        result = self.trial(report=[7, 0, 2, 512, 60_000_000, 0, 0, 2, 0, 0, 2, 0])
        self.assertEqual(result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
