"""Source-phase association uses full responses, never a header-only boundary."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ble_trial_report import capture_phase

SECOND = 1_000_000_000
EPISODES = [{'index': 0, 'register_requested_monotonic_ns': 10*SECOND,
             'registration_accepted_monotonic_ns': 11*SECOND,
             'unregister_requested_monotonic_ns': 20*SECOND,
             'unregistration_accepted_monotonic_ns': 21*SECOND,
             'release_monotonic_ns': None}]


class CapturePhaseTests(unittest.TestCase):
    def test_payload_crossing_removal_guard_is_not_source_on(self):
        row = {'command_start_ns': 18*SECOND, 'header_received_ns': 18*SECOND+500,
               'payload_received_ns': 19*SECOND+1}
        self.assertEqual(capture_phase(row, EPISODES), 'control_transition_guard_excluded')

    def test_full_response_inside_guard_is_source_on(self):
        row = {'command_start_ns': 12*SECOND, 'header_received_ns': 12*SECOND+500,
               'payload_received_ns': 13*SECOND}
        self.assertEqual(capture_phase(row, EPISODES), 'source_on_episode_0')

    def test_early_release_limits_source_phase(self):
        episode = {**EPISODES[0], 'release_monotonic_ns': 15*SECOND}
        row = {'command_start_ns': 14*SECOND, 'header_received_ns': 14*SECOND+500,
               'payload_received_ns': 15*SECOND}
        self.assertEqual(capture_phase(row, [episode]), 'control_transition_guard_excluded')

    def test_missing_or_reversed_full_bracket_cannot_establish_phase(self):
        self.assertEqual(capture_phase({'command_start_ns': 1, 'header_received_ns': 2}, EPISODES),
                         'capture_payload_timing_unknown_excluded')
        with self.assertRaises(ValueError):
            capture_phase({'command_start_ns': 1, 'header_received_ns': 3,
                           'payload_received_ns': 2}, EPISODES)


if __name__ == '__main__':
    unittest.main()
