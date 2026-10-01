"""Known synthetic FM validates the demodulator's independent frequency scale."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

MODULE = Path(__file__).resolve().parents[1] / "tools/analyze_rtl_fm.py"
spec = importlib.util.spec_from_file_location("rtl_fm_analysis", MODULE)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class KnownSignal(unittest.TestCase):
    def test_off_center_fm_pilot_is_at_nineteen_kilohertz(self):
        rate = 1024000
        times = np.arange(rate)/rate
        # Analytic FM carrier at +100 kHz with a 19 kHz modulator and 1 kHz deviation.
        phase = 2*np.pi*100000*times - (1000/19000)*np.cos(2*np.pi*19000*times)
        wave = 90*np.exp(1j*phase)
        raw = np.empty(2*rate, dtype=np.uint8)
        raw[::2] = np.round(127.5+wave.real).astype(np.uint8)
        raw[1::2] = np.round(127.5+wave.imag).astype(np.uint8)
        result, *_ = tool.analyze_samples(raw, {"sample_rate_hz": rate, "center_hz": 101000000, "candidate_channel_hz": 101100000})
        self.assertAlmostEqual(result["pilot_region_peak_hz"], 19000, delta=4)
        self.assertGreater(result["pilot_region_peak_vs_nearby_median_db"], 30)
        self.assertEqual(result["nominal_iq_duration_s"], 1)

    def test_partial_iq_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            tool.analyze_samples(np.zeros(2048001, dtype=np.uint8), {"sample_rate_hz": 1024000})


if __name__ == "__main__":
    unittest.main()
