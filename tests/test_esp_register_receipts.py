"""Host checks against real diagnostic C output with synthetic MMIO only."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import esp_register_receipts as host
import test_esp_register_observation_firmware as fixture

NONCE = '0123456789abcdef0123456789abcdef'


def frame(obj):
    body = json.dumps(obj, separators=(',', ':')).encode('ascii')
    return b'REGOBS1 %08x '%zlib.crc32(body)+body+b'\n'


def transcript(wire):
    """Independent extraction; feeds original CRC-framed C lines to host."""
    result = []
    pending = None
    pos = 0
    while pos < len(wire):
        stop = wire.index(b'\n', pos)+1
        line = wire[pos:stop]
        pos = stop
        if line.startswith(b'DATA '):
            _, count, crc, elapsed = line.decode().split()
            size = (int(count)*20+7)//8
            payload = wire[pos:pos+size]
            pos += size
            pending = (int(count), crc, int(elapsed), payload)
        elif line.startswith(b'REGOBS1 '):
            result.append((line, pending))
            pending = None
    return result


class HostActualCReceipts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.ActualReceiverC.setUpClass()
        cls.executable = fixture.ActualReceiverC.path/'check'
        cls.good = cls.output(0)

    @classmethod
    def tearDownClass(cls):
        fixture.ActualReceiverC.tearDownClass()

    @classmethod
    def output(cls, mode):
        result = subprocess.run([str(cls.executable), str(mode)],
                                check=True, capture_output=True, timeout=5)
        return transcript(result.stdout)

    def replay(self, rows, session=None):
        session = session or host.Session(NONCE, 100000)
        for index, (line, data) in enumerate(rows):
            session.consume(line, index*10+1, index*10+2, data=data)
        return session

    def test_actual_c_twenty_binary_frames_and_eighty_one_records(self):
        session = self.replay(self.good)
        self.assertEqual(session.state, 'completed')
        self.assertEqual(len(session.records), 81)
        self.assertEqual(len(session.captures), 20)
        self.assertEqual(len(session.receipts), 22)
        self.assertEqual(zlib.crc32(b'123456789'), 0xcbf43926)

    def test_actual_changed_selector_is_accepted_as_observation(self):
        session = self.replay(self.output(1))
        self.assertEqual(session.state, 'completed')
        self.assertEqual([r['selector'] for r in session.records[1:5]], [48,47,46,45])
        self.assertEqual(session.records[2]['bit23'], 0)

    def test_mutated_valid_crc_fields_fail_permanently(self):
        mutations = [
            lambda r: r.update(nonce='f'*32),
            lambda r: r.update(revision='regobs-v2'),
            lambda r: r.update(schema=True),
            lambda r: r.update(returned_samples=True),
            lambda r: r.update(returned_samples=16379),
            lambda r: r.update(payload_bytes=40949),
            lambda r: r.update(payload_crc32='00000000'),
            lambda r: r.update(completion=1),
            lambda r: r.update(capture_ordinal=1),
            lambda r: r.update(extra='untrusted'),
            lambda r: r['records'].pop(),
            lambda r: r['records'].append(copy.deepcopy(r['records'][0])),
            lambda r: r['records'].reverse(),
            lambda r: r['records'][0].update(sequence=True),
            lambda r: r['records'][0].update(sequence=0),
            lambda r: r['records'][0].update(read_begin_us=0),
            lambda r: r['records'][0].update(selector=128),
            lambda r: r['records'][0].update(bit23=True),
            lambda r: r['records'][0].update(read_end_us=1.5),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                obj = copy.deepcopy(host.parse_line(self.good[1][0]))
                mutation(obj)
                session = self.replay(self.good[:1])
                with self.assertRaises(host.ProtocolError):
                    session.consume(frame(obj), 11, 12, data=self.good[1][1])
                self.assertEqual(session.state, 'failed')
                self.assertEqual(len(session.records), 1)
                with self.assertRaises(host.ProtocolError):
                    session.consume(*[self.good[1][0], 21, 22], data=self.good[1][1])

    def test_wire_crc_duplicate_nested_keys_length_and_nonascii_rejected(self):
        good = self.good[0][0]
        obj = host.parse_line(good)
        body = json.dumps(obj, separators=(',', ':')).encode()
        duplicate = body.replace(b'"schema":1', b'"schema":1,"schema":1')
        nested = body.replace(b'"selector":48', b'"selector":48,"selector":48')
        for bad in (good.replace(b'REGOBS1 ', b'REGOBS1 0', 1),
                    b'REGOBS1 %08x '%zlib.crc32(duplicate)+duplicate+b'\n',
                    b'REGOBS1 %08x '%zlib.crc32(nested)+nested+b'\n',
                    good+b' '*2048, good[:-1], good.replace(b'1', b'\xff', 1)):
            with self.subTest(bad_length=len(bad)), self.assertRaises(host.ProtocolError):
                self.replay([(bad, None)])

    def test_payload_truncation_corruption_count_and_header_disagreement(self):
        count, crc, elapsed, payload = self.good[1][1]
        for bad in ((count,crc,elapsed,payload[:-1]),
                    (count,crc,elapsed,bytes([payload[0]^1])+payload[1:]),
                    (count-1,crc,elapsed,payload),
                    (count,crc,elapsed+1,payload), None):
            session = self.replay(self.good[:1])
            with self.assertRaises(host.ProtocolError):
                session.consume(self.good[1][0], 11, 12, data=bad)
            self.assertEqual(len(session.captures), 0)

    def test_early_terminal_deadline_and_host_regression_cannot_complete(self):
        session = self.replay(self.good[:1])
        with self.assertRaises(host.ProtocolError):
            session.consume(self.good[-1][0], 11, 12)
        for start, end in ((100000,100001), (100,100000), (10,9), (0,1)):
            session = self.replay(self.good[:-1])
            with self.assertRaises(host.ProtocolError):
                session.consume(self.good[-1][0], start, end)
            self.assertEqual(session.state, 'failed')

    def test_config_strict_profile_and_end_totals(self):
        for mutate in (lambda r:r['settings'].update(filter_code=48),
                       lambda r:r['settings'].update(gain_selector=True),
                       lambda r:r.update(profile='esp32-sdr'),
                       lambda r:r.update(start_us=-1)):
            obj = host.parse_line(self.good[0][0]); mutate(obj)
            with self.assertRaises(host.ProtocolError):
                self.replay([(frame(obj),None)])
        for mutate in (lambda r:r.update(record_count=80),
                       lambda r:r.update(pairs=327599),
                       lambda r:r.update(start_us=True),
                       lambda r:r.update(end_us=r['start_us']+30000001)):
            obj = host.parse_line(self.good[-1][0]); mutate(obj)
            session = self.replay(self.good[:-1])
            with self.assertRaises(host.ProtocolError):
                session.consume(frame(obj), 211, 212)

    def test_actual_timeout_memory_count_and_pre_begin_failures_stay_failed(self):
        for mode in (2,3,4,5,9,10,11,12,14,16,17):
            with self.subTest(mode=mode):
                session = self.replay(self.output(mode))
                self.assertEqual(session.state, 'failed')
                self.assertEqual(len(session.captures), 20 if mode == 16 else 0)
                with self.assertRaises(host.ProtocolError):
                    session.consume(self.good[-1][0], 211, 212)


if __name__ == '__main__':
    unittest.main()
