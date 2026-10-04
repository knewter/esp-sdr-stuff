"""Pure v1 finite source/batch codecs; no device, load or trial admission.

See firmware/forgix-synthetic-source/CODEC.md. Tick64 reconstruction depends
on a caller-supplied coherent START tick; it is not measured elapsed time.
"""
from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib

RECORD_BYTES = 16
FRAME_BYTES = 512
HEADER_BYTES = 64
MAX_RECORDS = 26
PROFILES = {2_000_000: 960, 500_000: 3840, 250_000: 7680}
_U32 = (1 << 32) - 1
_U64 = (1 << 64) - 1
_HEADER = struct.Struct('<4sBBHIHHHHQ16sIIIQ')


class Error(IntEnum):
    ARGUMENT = 1
    LENGTH = 2
    HEADER = 3
    FRAME_CRC = 4
    RECORD_CRC = 5
    NONCE = 6
    PROFILE = 7
    PATTERN = 8
    DUPLICATE = 9
    REORDER = 10
    GAP = 11
    TICK = 12
    TIMESTAMP = 13
    COUNT = 14
    CLOSED = 15
    TRUNCATED = 16
    CHUNK = 17


class CodecError(ValueError):
    def __init__(self, code, message, raw=b'', unconsumed=b''):
        super().__init__(message)
        self.code = code
        self.raw = raw
        self.unconsumed = unconsumed


def _uint(value, maximum):
    if type(value) is not int or not 0 <= value <= maximum:
        raise CodecError(Error.ARGUMENT, 'Unsigned integer required')
    return value


def _nonce(value):
    if type(value) is not bytes or len(value) != 16 or not any(value):
        raise CodecError(Error.NONCE, 'Nonzero 16-byte run nonce required')
    return value


def _profile(period, target):
    _uint(period, _U32)
    _uint(target, _U32)
    if PROFILES.get(period) != target:
        raise CodecError(Error.PROFILE, 'Exact finite profile required')


def pattern(sequence, nonce):
    sequence = _uint(sequence, _U32)
    words = struct.unpack('<4I', _nonce(nonce))
    result = sequence ^ ((sequence << 7 | sequence >> 25) & _U32) ^ 0x46534731
    for word in words:
        result ^= word
    return result


@dataclass(frozen=True)
class SourceRecord:
    sequence: int
    tick32: int
    pattern: int
    crc32: int

    @classmethod
    def create(cls, sequence, tick32, nonce):
        values = (_uint(sequence, _U32), _uint(tick32, _U32), pattern(sequence, nonce))
        raw = struct.pack('<3I', *values)
        return cls(*values, zlib.crc32(raw))

    def encode(self, nonce):
        values = tuple(_uint(n, _U32) for n in (self.sequence, self.tick32, self.pattern, self.crc32))
        _nonce(nonce)
        raw = struct.pack('<4I', *values)
        if zlib.crc32(raw[:12]) != self.crc32:
            raise CodecError(Error.RECORD_CRC, 'Source CRC differs', raw)
        if self.pattern != pattern(self.sequence, nonce):
            raise CodecError(Error.PATTERN, 'Source pattern differs', raw)
        return raw

    @classmethod
    def decode(cls, raw, nonce):
        if type(raw) is not bytes or len(raw) != RECORD_BYTES:
            raise CodecError(Error.LENGTH, 'Exact source record required', raw)
        return_value = cls(*struct.unpack('<4I', raw))
        return_value.encode(nonce)
        return return_value


@dataclass(frozen=True)
class Batch:
    frame_sequence: int
    device_time_us: int
    nonce: bytes
    period_cycles: int
    target_records: int
    records: tuple[SourceRecord, ...]

    @property
    def record_bytes(self):
        return len(self.records) * RECORD_BYTES

    @property
    def pattern_bytes(self):
        return len(self.records) * 4

    def encode(self):
        _uint(self.frame_sequence, _U32)
        _uint(self.device_time_us, _U64)
        _nonce(self.nonce)
        _profile(self.period_cycles, self.target_records)
        if type(self.records) is not tuple or not 1 <= len(self.records) <= MAX_RECORDS:
            raise CodecError(Error.COUNT, 'Batch requires 1..26 source records')
        if any(type(record) is not SourceRecord for record in self.records):
            raise CodecError(Error.ARGUMENT, 'Source records required')
        payload = b''.join(record.encode(self.nonce) for record in self.records)
        raw = bytearray(FRAME_BYTES)
        _HEADER.pack_into(raw, 0, b'FSB1', 1, 1, HEADER_BYTES, self.frame_sequence,
                          FRAME_BYTES, len(self.records), len(payload), 0, self.device_time_us,
                          self.nonce, self.records[0].sequence, self.period_cycles, self.target_records, 0)
        raw[HEADER_BYTES:HEADER_BYTES + len(payload)] = payload
        struct.pack_into('<I', raw, 508, zlib.crc32(raw[:508]))
        return bytes(raw)

    @classmethod
    def decode(cls, raw, expected_nonce):
        if type(raw) is not bytes or len(raw) != FRAME_BYTES:
            raise CodecError(Error.LENGTH, 'Exact 512-byte frame required', raw)
        _nonce(expected_nonce)
        fields = _HEADER.unpack_from(raw)
        magic, version, kind, header, seq, length, count, nbytes, reserved, stamp, nonce, first, period, target, reserved64 = fields
        if (magic, version, kind, header, length) != (b'FSB1', 1, 1, HEADER_BYTES, FRAME_BYTES):
            raise CodecError(Error.HEADER, 'Unknown frame header', raw)
        if not 1 <= count <= MAX_RECORDS or nbytes != count * RECORD_BYTES:
            raise CodecError(Error.COUNT, 'Invalid record count/length', raw)
        if reserved or reserved64 or any(raw[HEADER_BYTES + nbytes:508]):
            raise CodecError(Error.HEADER, 'Reserved/padding bytes must be zero', raw)
        if zlib.crc32(raw[:508]) != struct.unpack_from('<I', raw, 508)[0]:
            raise CodecError(Error.FRAME_CRC, 'Frame CRC differs', raw)
        if nonce != expected_nonce:
            raise CodecError(Error.NONCE, 'Wrong complete run nonce', raw)
        try:
            _profile(period, target)
        except CodecError as error:
            raise CodecError(error.code, str(error), raw) from error
        try:
            records = tuple(SourceRecord.decode(raw[offset:offset + RECORD_BYTES], nonce)
                            for offset in range(HEADER_BYTES, HEADER_BYTES + nbytes, RECORD_BYTES))
        except CodecError as error:
            raise CodecError(error.code, str(error), raw) from error
        if records[0].sequence != first:
            raise CodecError(Error.HEADER, 'First source sequence alias differs', raw)
        return cls(seq, stamp, nonce, period, target, records)


class Stream:
    """Atomic, fail-latched strict completeness; callers persist raw input first."""
    def __init__(self, nonce, period_cycles, target_records, start_tick64):
        self.nonce = _nonce(nonce)
        _profile(period_cycles, target_records)
        _uint(start_tick64, _U64)
        if start_tick64 > _U64 - period_cycles * target_records:
            raise CodecError(Error.TICK, 'Full finite tick range overflows uint64')
        self.period_cycles, self.target_records = period_cycles, target_records
        self.start_tick64 = start_tick64
        self.next_frame = self.next_record = 0
        self.last_device_time_us = None
        self.last_fpga_tick64 = start_tick64
        self.tick32_wraps = 0
        self.failure = None
        self.finished = False

    def _open(self):
        if self.failure is not None:
            raise self.failure
        if self.finished:
            raise CodecError(Error.CLOSED, 'Stream already finished')

    @staticmethod
    def _order(actual, expected):
        if actual != expected:
            code = Error.GAP if actual > expected else (Error.DUPLICATE if actual == expected - 1 else Error.REORDER)
            raise CodecError(code, f'Sequence {actual}, expected {expected}')

    def accept(self, raw):
        try:
            self._open()
            batch = Batch.decode(raw, self.nonce)
            if (batch.period_cycles, batch.target_records) != (self.period_cycles, self.target_records):
                raise CodecError(Error.PROFILE, 'Run profile differs')
            self._order(batch.frame_sequence, self.next_frame)
            if self.last_device_time_us is not None and batch.device_time_us < self.last_device_time_us:
                raise CodecError(Error.TIMESTAMP, 'Device timestamp decreased')
            if self.next_record + len(batch.records) > self.target_records:
                raise CodecError(Error.COUNT, 'Source exceeds finite target')
            for index, record in enumerate(batch.records, self.next_record):
                self._order(record.sequence, index)
                tick64 = self.start_tick64 + (index + 1) * self.period_cycles
                if record.tick32 != tick64 & _U32:
                    raise CodecError(Error.TICK, 'Source tick differs from anchored profile')
            self.next_frame += 1
            self.next_record += len(batch.records)
            self.last_device_time_us = batch.device_time_us
            self.last_fpga_tick64 = tick64
            self.tick32_wraps = (tick64 >> 32) - (self.start_tick64 >> 32)
            return batch
        except CodecError as error:
            if self.failure is None:
                self.failure = CodecError(error.code, str(error), raw)
            raise self.failure

    def finish(self):
        try:
            self._open()
            if self.next_record != self.target_records:
                raise CodecError(Error.COUNT, 'Finite target is incomplete')
            self.finished = True
        except CodecError as error:
            if self.failure is None:
                self.failure = error
            raise self.failure


class Fragments:
    """Bounded chunk assembly; failures retain the exact frame/prefix and suffix."""
    def __init__(self, stream):
        self.stream = stream
        self.pending = b''

    def feed(self, chunk):
        if self.stream.failure is not None:
            raise self.stream.failure
        if self.stream.finished:
            self.stream.failure = CodecError(Error.CLOSED, 'Stream already finished', self.pending, chunk)
            raise self.stream.failure
        if type(chunk) is not bytes or len(chunk) > FRAME_BYTES:
            self.stream.failure = CodecError(Error.CHUNK, 'At most 512-byte chunks required', self.pending, chunk)
            raise self.stream.failure
        data = self.pending + chunk
        accepted = []
        self.pending = b''
        while len(data) >= FRAME_BYTES:
            raw, data = data[:FRAME_BYTES], data[FRAME_BYTES:]
            try:
                accepted.append(self.stream.accept(raw))
            except CodecError as error:
                error.unconsumed = data
                raise
        self.pending = data
        return tuple(accepted)

    def finish(self):
        if self.stream.failure is not None:
            raise self.stream.failure
        if self.pending:
            self.stream.failure = CodecError(Error.TRUNCATED, 'Partial frame at EOF', self.pending)
            raise self.stream.failure
        self.stream.finish()
