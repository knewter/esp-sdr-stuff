"""Source-phase association uses full responses, never a header-only boundary."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ble_trial_report import capture_phase, complete_owned_packets

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


def packet(offset=1000, period=4):
    start=offset-8*period*4
    return dict(status='valid_owned', crc24_ok=True, owned_manufacturer_ad_exact_match=True,
                pdu_type=2, access_address_hamming_errors=0, preamble_hamming_errors=0,
                pdu_sha256='a'*64, access_address_sample_offset=offset, access_correlation=.95,
                samples_per_symbol_at_4msps=period, pdu_length=22, packet_duration_us=256,
                nominal_packet_start_sample=start, nominal_packet_end_sample=start+256*period*4,
                complete_preamble_and_pdu_crc_within_capture_nominal=True)


class CompletePacketTests(unittest.TestCase):
    def select(self,frames):return complete_owned_packets(frames,16380,16000000)

    def test_complete_protected_owned_packet_is_retained(self):
        accepted,excluded=self.select([packet(period=3.995)])
        self.assertEqual(len(accepted),1);self.assertEqual(excluded,[])

    def test_status_alone_and_coarse_missing_bounds_are_not_complete(self):
        coarse=packet()
        for key in ('nominal_packet_start_sample','nominal_packet_end_sample',
                    'complete_preamble_and_pdu_crc_within_capture_nominal','samples_per_symbol_at_4msps'):
            coarse.pop(key)
        accepted,excluded=self.select([coarse,dict(status='valid_owned')])
        self.assertEqual(accepted,[]);self.assertEqual(len(excluded),2)
        self.assertTrue(all('complete_nominal_packet_window_unverified' in r['exclusion_reasons'] for r in excluded))

    def test_clipped_preamble_and_crc_windows_are_excluded(self):
        for candidate in (packet(offset=20),packet(offset=16000),
                          {**packet(),'complete_preamble_and_pdu_crc_within_capture_nominal':False}):
            with self.subTest(candidate=candidate):
                accepted,excluded=self.select([candidate])
                self.assertEqual(accepted,[])
                self.assertIn('complete_nominal_packet_window_unverified',excluded[0]['exclusion_reasons'])

    def test_crc_marker_hash_and_finite_consistent_bounds_required(self):
        for key,value in [('crc24_ok',False),('owned_manufacturer_ad_exact_match',False),
                          ('pdu_sha256','a'*63),('nominal_packet_start_sample',float('nan')),
                          ('nominal_packet_end_sample',float('inf')),('samples_per_symbol_at_4msps',3.96),
                          ('samples_per_symbol_at_4msps',True),('nominal_packet_start_sample',900),
                          ('packet_duration_us',255),('pdu_length',23)]:
            with self.subTest(key=key,value=value):
                accepted,excluded=self.select([{**packet(),key:value}])
                self.assertEqual(accepted,[]);self.assertEqual(len(excluded),1)

    def test_actual_packet_type_and_aa_preamble_diagnostics_are_required(self):
        for key,value in [('pdu_type',None),('pdu_type',1),('access_address_hamming_errors',None),
                          ('access_address_hamming_errors',3),('preamble_hamming_errors',None),
                          ('preamble_hamming_errors',9)]:
            with self.subTest(key=key,value=value):
                accepted,excluded=self.select([{**packet(),key:value}])
                self.assertEqual(accepted,[])
                self.assertIn('packet_type_or_aa_preamble_diagnostics_unverified',excluded[0]['exclusion_reasons'])

    def test_contradictory_protected_pdu_hashes_cannot_be_silently_deduplicated(self):
        for complete in (True,False):
            conflict={**packet(offset=1002),'pdu_sha256':'b'*64,
                      'complete_preamble_and_pdu_crc_within_capture_nominal':complete}
            accepted,excluded=self.select([packet(),conflict])
            self.assertEqual(accepted,[]);self.assertEqual(len(excluded),2)
            self.assertTrue(all('conflicting_protected_pdu_hashes_in_access_address_cluster' in r['exclusion_reasons'] for r in excluded))

    def test_duplicate_hypotheses_count_once_and_incomplete_cannot_suppress_full(self):
        full=packet();duplicate={**packet(offset=1002),'access_correlation':.9}
        clipped={**packet(),'access_correlation':.99,'complete_preamble_and_pdu_crc_within_capture_nominal':False}
        accepted,excluded=self.select([duplicate,clipped,full,packet(offset=7000)])
        self.assertEqual([f['access_address_sample_offset'] for f in accepted],[1000,7000])
        self.assertEqual(len(excluded),2)
        self.assertIn('duplicate_access_address_receiver_hypothesis',excluded[1]['exclusion_reasons'])


if __name__ == '__main__':
    unittest.main()
