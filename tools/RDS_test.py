"""Guard against counting inherited PI fields as directly valid block A."""
import json
import unittest
from RDS_trial import summarize


class RdsEvidenceTests(unittest.TestCase):
    def test_inherited_identity_is_not_direct_pi_proof(self):
        lines = "\n".join(json.dumps(r) for r in [
            {"pi": "0x9250", "raw_data": "9250 2280 0000 0000", "time_from_start": 1.},
            {"pi": "0x9250", "raw_data": "---- 2280 0000 0000", "time_from_start": 2.},
            {"pi": "0x9250", "raw_data": "---- ---- ---- 0000"}])
        got = summarize(lines)
        self.assertEqual(got["direct_valid_block_a_pi_counts"], {"0x9250": 1})
        self.assertEqual(got["complete_four_block_groups"], 1)
        self.assertEqual(got["valid_blocks_in_emitted_groups"], 8)
        self.assertEqual(got["last_group_time_s"], 2.)


if __name__ == "__main__":
    unittest.main()
