"""Actual native C versus Python/zlib and literal wire fixtures; no hardware."""
import ctypes as C
from dataclasses import replace
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import forgix_synthetic_codec as py

NONCE = bytes(range(16))  # Nonzero128bits whose XOR fold is zero.
RECORD = bytes.fromhex('0000000080841e00314753460c00005e')
HEADER = bytes.fromhex('465342310101400000000000000201001000000015cd5b0700000000'
                       '000102030405060708090a0b0c0d0e0f0000000080841e00c00300000000000000000000')
LITERAL_FRAME = HEADER + RECORD + bytes(428) + bytes.fromhex('ebd67710')


class Record(C.Structure):
    _fields_ = [(n, C.c_uint32) for n in ('sequence', 'tick32', 'pattern', 'crc32')]


class Batch(C.Structure):
    _fields_ = [('frame_sequence', C.c_uint32), ('device_time_us', C.c_uint64),
                ('nonce', C.c_uint8 * 16), ('period_cycles', C.c_uint32),
                ('target_records', C.c_uint32), ('count', C.c_uint16), ('records', Record * 26)]


class State(C.Structure):
    _fields_ = [('nonce', C.c_uint8 * 16)] + [(n, C.c_uint32) for n in
                ('period_cycles', 'target_records', 'next_frame', 'next_record')] + [
                (n, C.c_uint64) for n in ('start_tick64', 'last_device_time_us', 'last_fpga_tick64')] + [
                ('tick32_wraps', C.c_uint32), ('failure', C.c_int), ('failed', C.c_bool),
                ('have_timestamp', C.c_bool), ('finished', C.c_bool)]


def buffer(raw):
    return C.create_string_buffer(raw, max(1, len(raw)))


def outer_crc(raw):
    raw = bytearray(raw)
    struct.pack_into('<I', raw, 508, zlib.crc32(raw[:508]))
    return bytes(raw)


def frame(first=0, count=26, seq=0, stamp=1, period=2_000_000, start=0, nonce=NONCE):
    records = tuple(py.SourceRecord.create(i, (start + (i + 1) * period) & 0xffffffff, nonce)
                    for i in range(first, first + count))
    return py.Batch(seq, stamp, nonce, period, py.PROFILES[period], records)


class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cc = shutil.which('cc')
        if not cc or not str(Path(cc).resolve()).startswith('/nix/store/'):
            raise RuntimeError('Use the locked Nix compiler')
        cls.tmp = tempfile.TemporaryDirectory()
        output = Path(cls.tmp.name) / 'codec.so'
        subprocess.run([cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC',
                        '-fsanitize=undefined', '-fno-sanitize-recover=undefined',
                        str(ROOT / 'firmware/forgix-synthetic-source/codec.c'), '-o', str(output)],
                       check=True, capture_output=True, timeout=30)
        cls.lib = C.CDLL(str(output))
        signatures = {
            'fsg_crc32': ([C.c_void_p, C.c_size_t], C.c_uint32),
            'fsg_record_create': ([C.c_uint32, C.c_uint32, C.c_void_p, C.POINTER(Record)], C.c_int),
            'fsg_record_encode': ([C.POINTER(Record), C.c_void_p, C.c_void_p], C.c_int),
            'fsg_record_decode': ([C.c_void_p, C.c_size_t, C.c_void_p, C.POINTER(Record)], C.c_int),
            'fsg_batch_encode': ([C.POINTER(Batch), C.c_void_p], C.c_int),
            'fsg_batch_decode': ([C.c_void_p, C.c_size_t, C.c_void_p, C.POINTER(Batch)], C.c_int),
            'fsg_stream_init': ([C.POINTER(State), C.c_void_p, C.c_uint32, C.c_uint32, C.c_uint64], C.c_int),
            'fsg_stream_accept': ([C.POINTER(State), C.c_void_p, C.c_size_t], C.c_int),
            'fsg_stream_finish': ([C.POINTER(State)], C.c_int),
        }
        for name, (args, result) in signatures.items():
            function = getattr(cls.lib, name)
            function.argtypes, function.restype = args, result

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def native_batch(self, batch):
        value = Batch()
        value.frame_sequence, value.device_time_us = batch.frame_sequence, batch.device_time_us
        value.nonce[:] = batch.nonce
        value.period_cycles, value.target_records = batch.period_cycles, batch.target_records
        value.count = len(batch.records)
        for i, record in enumerate(batch.records):
            value.records[i] = Record(record.sequence, record.tick32, record.pattern, record.crc32)
        return value

    def encode(self, batch):
        native = self.native_batch(batch)
        out = C.create_string_buffer(512)
        self.assertEqual(self.lib.fsg_batch_encode(C.byref(native), out), 0)
        self.assertEqual(out.raw, batch.encode())
        return out.raw

    def decode(self, raw, nonce=NONCE):
        out = Batch()
        C.memset(C.byref(out), 0xa5, C.sizeof(out))
        before = bytes(out)
        error = self.lib.fsg_batch_decode(buffer(raw), len(raw), buffer(nonce), C.byref(out))
        try:
            batch = py.Batch.decode(raw, nonce)
        except py.CodecError as expected:
            self.assertEqual(error, expected.code)
            self.assertEqual(bytes(out), before, 'C output changed on refusal')
            return error
        self.assertEqual(error, 0)
        self.assertEqual(out.frame_sequence, batch.frame_sequence)
        self.assertEqual(out.device_time_us, batch.device_time_us)
        self.assertEqual(bytes(out.nonce), batch.nonce)
        self.assertEqual((out.period_cycles, out.target_records, out.count),
                         (batch.period_cycles, batch.target_records, len(batch.records)))
        self.assertEqual([tuple(getattr(out.records[i], n) for n in ('sequence', 'tick32', 'pattern', 'crc32'))
                          for i in range(out.count)],
                         [(r.sequence, r.tick32, r.pattern, r.crc32) for r in batch.records])
        return error

    def streams(self, period=2_000_000, start=0):
        s = State()
        self.assertEqual(self.lib.fsg_stream_init(C.byref(s), buffer(NONCE), period, py.PROFILES[period], start), 0)
        return s, py.Stream(NONCE, period, py.PROFILES[period], start)

    def accept(self, native, python, raw):
        status = self.lib.fsg_stream_accept(C.byref(native), buffer(raw), len(raw))
        try:
            python.accept(raw)
        except py.CodecError as error:
            self.assertEqual(status, error.code)
        else:
            self.assertEqual(status, 0)
        self.assertEqual((native.next_frame, native.next_record, native.last_fpga_tick64, native.tick32_wraps),
                         (python.next_frame, python.next_record, python.last_fpga_tick64, python.tick32_wraps))
        self.assertEqual(native.failed, python.failure is not None)
        return status

    def test_literal_record_frame_and_independent_crc_vector(self):
        self.assertEqual(self.lib.fsg_crc32(buffer(b'123456789'), 9), 0xcbf43926)
        self.assertEqual(zlib.crc32(b'123456789'), 0xcbf43926)
        self.assertEqual(self.lib.fsg_crc32(None, 0), 0)
        self.assertEqual(len(LITERAL_FRAME), 512)
        self.assertEqual(zlib.crc32(RECORD[:12]), 0x5e00000c)
        self.assertEqual(zlib.crc32(LITERAL_FRAME[:508]), 0x1077d6eb)
        record = Record()
        self.assertEqual(self.lib.fsg_record_decode(buffer(RECORD), 16, buffer(NONCE), C.byref(record)), 0)
        self.assertEqual((record.sequence, record.tick32, record.pattern, record.crc32),
                         (0, 2_000_000, 0x46534731, 0x5e00000c))
        batch = frame(count=1, stamp=123456789)
        self.assertEqual(self.encode(batch), LITERAL_FRAME)
        self.assertEqual(self.decode(LITERAL_FRAME), 0)
        self.assertEqual((batch.record_bytes, batch.pattern_bytes), (16, 4))
        self.assertEqual((frame().record_bytes, frame().pattern_bytes), (416, 104))

    def test_native_record_constructor_independent_words_crc_and_endian(self):
        rng = random.Random(1933)
        cases = [(a, b, NONCE) for a in (0, 1, 0x80000000, 0xffffffff) for b in (0, 1, 0xffffffff)]
        cases += [(rng.randrange(2**32), rng.randrange(2**32), rng.randbytes(16)) for _ in range(200)]
        for seq, tick, nonce in cases:
            value = Record()
            self.assertEqual(self.lib.fsg_record_create(seq, tick, buffer(nonce), C.byref(value)), 0)
            known = (seq ^ ((seq << 7 | seq >> 25) & 0xffffffff) ^ 0x46534731)
            for offset in range(0, 16, 4):
                known ^= sum(nonce[offset+i] << (8*i) for i in range(4))
            literal = struct.pack('<3I', seq, tick, known)
            literal += struct.pack('<I', zlib.crc32(literal))
            out = C.create_string_buffer(16)
            self.assertEqual(self.lib.fsg_record_encode(C.byref(value), buffer(nonce), out), 0)
            self.assertEqual(out.raw, literal)
            self.assertEqual(py.SourceRecord.create(seq, tick, nonce).encode(nonce), literal)

    def test_record_damage_never_repaired_every_bit_and_partial_length(self):
        for offset in range(16):
            for bit in range(8):
                raw = bytearray(RECORD); raw[offset] ^= 1 << bit
                value = Record(); C.memset(C.byref(value), 0xa5, C.sizeof(value)); before = bytes(value)
                self.assertEqual(self.lib.fsg_record_decode(buffer(bytes(raw)), 16, buffer(NONCE), C.byref(value)), py.Error.RECORD_CRC)
                self.assertEqual(bytes(value), before)
                with self.assertRaises(py.CodecError): py.SourceRecord.decode(bytes(raw), NONCE)
        wrong_endian = b''.join(RECORD[i:i+4][::-1] for i in range(0, 16, 4))
        self.assertEqual(self.lib.fsg_record_decode(buffer(wrong_endian), 16, buffer(NONCE), C.byref(Record())), py.Error.RECORD_CRC)
        for length in range(16):
            value = Record()
            self.assertEqual(self.lib.fsg_record_decode(buffer(RECORD[:length]), length, buffer(NONCE), C.byref(value)), py.Error.LENGTH)
        damaged = replace(py.SourceRecord.decode(RECORD, NONCE), crc32=0)
        out = C.create_string_buffer(bytes([0xa5]) * 16, 16)
        value = Record(damaged.sequence, damaged.tick32, damaged.pattern, damaged.crc32)
        self.assertEqual(self.lib.fsg_record_encode(C.byref(value), buffer(NONCE), out), py.Error.RECORD_CRC)
        self.assertEqual(out.raw, bytes([0xa5]) * 16)
        with self.assertRaises(py.CodecError): damaged.encode(NONCE)

    def test_every_frame_bit_flip_refused_in_both_codecs(self):
        raw = self.encode(frame())
        for offset in range(512):
            for bit in range(8):
                changed = bytearray(raw); changed[offset] ^= 1 << bit
                self.assertNotEqual(self.decode(bytes(changed)), 0, (offset, bit))

    def test_every_reserved_padding_and_source_byte_mutation_with_repaired_outer_crc(self):
        for count in (1, 26):
            raw = self.encode(frame(count=count))
            offsets = [18, 19] + list(range(56, 64)) + list(range(64 + 16 * count, 508))
            for offset in offsets:
                for bit in range(8):
                    changed = bytearray(raw); changed[offset] = 1 << bit
                    self.assertEqual(self.decode(outer_crc(changed)), py.Error.HEADER)
            for offset in range(64, 64 + 16 * count):
                changed = bytearray(raw); changed[offset] ^= 1
                self.assertEqual(self.decode(outer_crc(changed)), py.Error.RECORD_CRC)

    def test_all_structural_fields_counts_lengths_profiles_and_source_alias(self):
        raw = self.encode(frame())
        mutations = [(i, 'B', v) for i in range(4) for v in (0, 255)]
        mutations += [(4, 'B', 0), (4, 'B', 2), (5, 'B', 0), (5, 'B', 2)]
        for offset, values in ((6, (0, 63, 65, 65535)), (12, (0, 511, 513, 65535)),
                               (14, (0, 27, 65535)), (16, (0, 415, 417, 65535))):
            mutations += [(offset, 'H', value) for value in values]
        for offset, values in ((44, (1, 0xffffffff)), (48, (0, 1, 1999999)), (52, (0, 1, 959, 961))):
            mutations += [(offset, 'I', value) for value in values]
        for offset, kind, value in mutations:
            changed = bytearray(raw); struct.pack_into('<' + kind, changed, offset, value)
            self.assertNotEqual(self.decode(outer_crc(changed)), 0, (offset, kind, value))
        for count in (1, 2, 25, 26): self.assertEqual(self.decode(self.encode(frame(count=count))), 0)
        for count in (0, 27):
            bad = replace(frame(), records=tuple(py.SourceRecord.create(i, 0, NONCE) for i in range(count)))
            value = self.native_batch(bad) if count <= 26 else self.native_batch(frame())
            value.count = count; output = C.create_string_buffer(bytes([0xa5]) * 512, 512)
            self.assertEqual(self.lib.fsg_batch_encode(C.byref(value), output), py.Error.COUNT)
            self.assertEqual(output.raw, bytes([0xa5]) * 512)
            with self.assertRaises(py.CodecError): bad.encode()

    def test_full_nonce_collision_pattern_and_binding_are_distinct(self):
        # Change two nonce words by the same XOR: identical pattern fold, different full nonce.
        collision = bytearray(NONCE); collision[0] ^= 1; collision[4] ^= 1; collision = bytes(collision)
        self.assertNotEqual(collision, NONCE)
        self.assertEqual(py.pattern(17, collision), py.pattern(17, NONCE))
        self.assertEqual(py.SourceRecord.decode(RECORD, collision).encode(collision), RECORD)
        self.assertEqual(self.decode(LITERAL_FRAME, collision), py.Error.NONCE)
        for offset in range(28, 44):
            changed = bytearray(LITERAL_FRAME); changed[offset] ^= 1
            self.assertEqual(self.decode(outer_crc(changed)), py.Error.NONCE)
        changed = bytearray(LITERAL_FRAME); changed[72] ^= 1
        struct.pack_into('<I', changed, 76, zlib.crc32(changed[64:76]))
        self.assertEqual(self.decode(outer_crc(changed)), py.Error.PATTERN)
        self.assertEqual(self.decode(LITERAL_FRAME, bytes(16)), py.Error.NONCE)

    def test_full_finite_runs_all_profiles_timestamps_and_tick_wraps(self):
        for period, target in py.PROFILES.items():
            start = (3 << 32) + 0xffffffff - period // 2
            native, python = self.streams(period, start)
            for index, first in enumerate(range(0, target, 26)):
                raw = self.encode(frame(first, min(26, target-first), index, index//2, period, start))
                self.assertEqual(self.accept(native, python, raw), 0)
            self.assertEqual(native.next_record, target)
            self.assertEqual(native.tick32_wraps, 1)
            self.assertEqual(native.last_fpga_tick64, start+period*target)
            self.assertEqual(self.lib.fsg_stream_finish(C.byref(native)), 0)
            python.finish(); self.assertTrue(native.finished and python.finished)
            self.assertEqual(self.lib.fsg_stream_finish(C.byref(native)), py.Error.CLOSED)
            with self.assertRaises(py.CodecError) as failure: python.finish()
            self.assertEqual(failure.exception.code, py.Error.CLOSED)

    def test_atomic_fail_latch_duplicate_reorder_gap_tick_profile_and_time(self):
        for bad, expected in ((frame(seq=1), py.Error.GAP), (frame(first=1), py.Error.GAP),
                              (frame(period=500_000), py.Error.PROFILE), (frame(start=1), py.Error.TICK)):
            native, python = self.streams()
            self.assertEqual(self.accept(native, python, bad.encode()), expected)
            self.assertEqual((native.next_frame, native.next_record), (0, 0))
            self.assertEqual(self.accept(native, python, frame().encode()), expected)
            self.assertEqual(python.failure.raw, bad.encode())
        for sequence, expected in ((4, py.Error.DUPLICATE), (2, py.Error.REORDER), (7, py.Error.GAP)):
            records = list(frame().records); records[5] = py.SourceRecord.create(sequence, 12_000_000, NONCE)
            bad = replace(frame(), records=tuple(records)); self.assertEqual(self.decode(bad.encode()), 0)
            native, python = self.streams(); self.assertEqual(self.accept(native, python, bad.encode()), expected)
            self.assertEqual(native.next_record, 0)  # First5 valid records in rejected frame are not committed.
        for bad, expected in ((frame(first=26, seq=0), py.Error.DUPLICATE),
                              (frame(first=25, seq=1), py.Error.DUPLICATE),
                              (frame(first=24, seq=1), py.Error.REORDER),
                              (frame(first=27, seq=1), py.Error.GAP),
                              (frame(first=26, seq=2), py.Error.GAP),
                              (frame(first=26, seq=1, stamp=0), py.Error.TIMESTAMP)):
            native, python = self.streams(); self.accept(native, python, frame().encode())
            self.assertEqual(self.accept(native, python, bad.encode()), expected)
            self.assertEqual((native.next_frame, native.next_record), (1, 26))
        native, python = self.streams()
        self.accept(native, python, frame(stamp=2**64-1).encode())
        self.assertEqual(self.accept(native, python, frame(first=26, seq=1, stamp=0).encode()), py.Error.TIMESTAMP)
        native, python = self.streams()
        self.assertEqual(self.accept(native, python, frame(first=0xffffffff, count=1).encode()), py.Error.GAP)
        # Frame sequence cannot roll over in a finite7680-record run.
        native, python = self.streams()
        self.assertEqual(self.accept(native, python, frame(seq=0xffffffff).encode()), py.Error.GAP)

    def test_target_overrun_early_finish_late_corruption_and_closed_stream(self):
        native, python = self.streams()
        self.assertEqual(self.lib.fsg_stream_finish(C.byref(native)), py.Error.COUNT)
        with self.assertRaises(py.CodecError): python.finish()
        self.assertEqual(self.accept(native, python, LITERAL_FRAME), py.Error.COUNT)
        native, python = self.streams()
        for index, first in enumerate(range(0, 936, 26)):
            self.accept(native, python, frame(first, 26, index).encode())
        self.assertEqual(self.accept(native, python, frame(936, 25, 36).encode()), py.Error.COUNT)
        self.assertEqual(native.next_record, 936)
        native, python = self.streams()
        for index, first in enumerate(range(0, 960, 26)):
            self.accept(native, python, frame(first, min(26, 960-first), index).encode())
        self.assertEqual(self.lib.fsg_stream_finish(C.byref(native)), 0); python.finish()
        self.assertEqual(self.accept(native, python, frame(960, 1, 37).encode()), py.Error.CLOSED)

    def test_every_partial_frame_length_and_extra_bytes_refused_without_resync(self):
        raw = self.encode(frame())
        for length in range(512):
            self.assertEqual(self.decode(raw[:length]), py.Error.LENGTH)
            native, python = self.streams()
            self.assertEqual(self.accept(native, python, raw[:length]), py.Error.LENGTH)
            self.assertEqual(self.accept(native, python, raw), py.Error.LENGTH)
        self.assertEqual(self.decode(raw+b'x'), py.Error.LENGTH)
        self.assertEqual(self.decode(raw+raw), py.Error.LENGTH)
        native, python = self.streams()
        self.assertEqual(self.accept(native, python, b'x'+raw[:-1]), py.Error.HEADER)

    def test_every_fragment_boundary_prefix_retention_and_eof(self):
        raw = self.encode(frame())
        next_raw = self.encode(frame(26, 26, 1))
        for split in range(1, 512):
            stream = py.Stream(NONCE, 2_000_000, 960, 0); fragments = py.Fragments(stream)
            self.assertEqual(fragments.feed(raw[:split]), ())
            self.assertEqual(fragments.pending, raw[:split])
            self.assertEqual(len(fragments.feed(raw[split:])), 1)
            self.assertEqual(len(fragments.feed(next_raw)), 1)
            self.assertEqual((stream.next_frame, stream.next_record), (2, 52))
            self.assertEqual(fragments.pending, b'')
            stream = py.Stream(NONCE, 2_000_000, 960, 0); fragments = py.Fragments(stream)
            fragments.feed(raw[:split])
            with self.assertRaises(py.CodecError) as failure: fragments.finish()
            self.assertEqual((failure.exception.code, failure.exception.raw), (py.Error.TRUNCATED, raw[:split]))
        stream = py.Stream(NONCE, 2_000_000, 960, 0); fragments = py.Fragments(stream)
        fragments.feed(b'BADMAGC')
        with self.assertRaises(py.CodecError) as failure: fragments.feed(raw[7:]+b'TAIL123')
        error = failure.exception
        self.assertEqual(error.raw, b'BADMAGC'+raw[7:]); self.assertEqual(error.unconsumed, b'TAIL123')
        with self.assertRaises(py.CodecError) as again: fragments.feed(raw)
        self.assertIs(again.exception, error)
        stream = py.Stream(NONCE, 2_000_000, 960, 0); fragments = py.Fragments(stream)
        fragments.feed(raw[:3])
        with self.assertRaises(py.CodecError) as failure: fragments.feed(raw+b'X')
        self.assertEqual((failure.exception.raw, failure.exception.unconsumed), (raw[:3], raw+b'X'))

    def test_fragment_finish_requires_exact_target_and_no_trailing_partial(self):
        for trailing in (b'', b'X'):
            stream = py.Stream(NONCE, 2_000_000, 960, 0); fragments = py.Fragments(stream)
            for index, first in enumerate(range(0, 960, 26)):
                fragments.feed(frame(first, min(26, 960-first), index).encode())
            fragments.feed(trailing)
            if trailing:
                with self.assertRaises(py.CodecError) as failure: fragments.finish()
                self.assertEqual(failure.exception.code, py.Error.TRUNCATED)
                self.assertEqual(failure.exception.raw, trailing)
            else:
                fragments.finish(); self.assertTrue(stream.finished)
                with self.assertRaises(py.CodecError) as failure: fragments.feed(b'')
                self.assertEqual(failure.exception.code, py.Error.CLOSED)

    def test_invalid_anchor_profile_nonce_types_and_native_pointer_errors(self):
        for nonce, period, target, start, expected in (
                (bytes(16), 2_000_000, 960, 0, py.Error.NONCE),
                (NONCE, 2_000_001, 960, 0, py.Error.PROFILE),
                (NONCE, 2_000_000, 959, 0, py.Error.PROFILE),
                (NONCE, 2_000_000, 960, 2**64-1, py.Error.TICK)):
            state = State(); self.assertEqual(self.lib.fsg_stream_init(C.byref(state), buffer(nonce), period, target, start), expected)
            self.assertTrue(state.failed); self.assertEqual(state.failure, expected)
            with self.assertRaises(py.CodecError) as failure: py.Stream(nonce, period, target, start)
            self.assertEqual(failure.exception.code, expected)
        for field, value in (('frame_sequence', True), ('frame_sequence', -1), ('frame_sequence', 2**32),
                             ('device_time_us', 1.0), ('device_time_us', 2**64), ('nonce', bytearray(NONCE)),
                             ('period_cycles', True), ('target_records', 960.0)):
            with self.assertRaises(py.CodecError): replace(frame(), **{field:value}).encode()
        self.assertEqual(self.lib.fsg_record_decode(None, 16, buffer(NONCE), C.byref(Record())), py.Error.ARGUMENT)
        self.assertEqual(self.lib.fsg_batch_decode(None, 512, buffer(NONCE), C.byref(Batch())), py.Error.ARGUMENT)
        self.assertEqual(self.lib.fsg_stream_finish(None), py.Error.ARGUMENT)
        state, _ = self.streams(start=2**64-1-2_000_000*960)
        self.assertFalse(state.failed)  # Exact uint64 bound remains representable.

    def test_native_alias_buffers_and_encoder_refusal_leave_output_intact(self):
        expected = frame(count=1, stamp=123456789)
        memory = C.create_string_buffer(512); native = Batch.from_buffer(memory)
        C.memmove(C.byref(native), C.byref(self.native_batch(expected)), C.sizeof(Batch))
        self.assertEqual(self.lib.fsg_batch_encode(C.byref(native), memory), 0)
        self.assertEqual(memory.raw, LITERAL_FRAME)
        state = State(); state.nonce[:] = NONCE
        self.assertEqual(self.lib.fsg_stream_init(C.byref(state), state.nonce, 2_000_000, 960, 0), 0)
        self.assertEqual(bytes(state.nonce), NONCE)
        native = self.native_batch(frame()); native.records[25].crc32 ^= 1
        memory = C.create_string_buffer(bytes([0xa5])*512, 512)
        self.assertEqual(self.lib.fsg_batch_encode(C.byref(native), memory), py.Error.RECORD_CRC)
        self.assertEqual(memory.raw, bytes([0xa5])*512)


if __name__ == '__main__':
    unittest.main(verbosity=2)
