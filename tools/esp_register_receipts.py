"""Strict register-observation receipt validation; no hardware operations.

This module accepts only the separate regobs-v1 protocol. A transport operator
must supply independently verified DATA header/payload bytes and host brackets.
Any invalid receipt permanently fails the session; it cannot be resynchronized.
"""
import json
import re
import zlib

PROFILE = 'esp32-register-observation-v1'
REVISION = 'regobs-v1'
INFO = 'ESP32REGOBS1 regobs-v1 burst 16380'
SETTINGS = dict(frequency_mhz=2401, bandwidth_mhz=20, filter_code=64,
                gain_mode='MANUAL', gain_selector=48)
COMMON = {'schema', 'kind', 'nonce', 'revision'}
STAGES = ('before_acquire', 'armed_before_trigger', 'dump_complete',
          'restored_after_dump')
FAILURES = {'capture_timeout', 'capture_count', 'capture_memory',
            'record_capacity', 'session_deadline', 'session_state'}
RECORD_KEYS = {'sequence', 'capture_ordinal', 'stage', 'read_begin_us',
               'read_end_us', 'selector', 'bit23'}


class ProtocolError(ValueError):
    """Safe fixed message; never include untrusted wire contents."""


def require(condition, message):
    if not condition:
        raise ProtocolError(message)


def integer(value, minimum=0, maximum=(1 << 63)-1):
    require(type(value) is int and minimum <= value <= maximum,
            'Invalid integer field')
    return value


def exact(value, expected):
    require(type(value) is type(expected) and value == expected,
            'Fixed protocol field mismatch')


def keys(value, expected):
    require(type(value) is dict and set(value) == set(expected),
            'Receipt field allowlist mismatch')


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, 'Duplicate JSON key')
        obj[key] = value
    return obj


def parse_line(line):
    require(type(line) is bytes and len(line) <= 2048,
            'Receipt line budget exceeded')
    match = re.fullmatch(rb'REGOBS1 ([0-9a-f]{8}) ([^\r\n]+)\n', line)
    require(match is not None, 'Invalid receipt framing')
    body = match[2]
    require(zlib.crc32(body) == int(match[1], 16), 'Receipt CRC mismatch')
    try:
        text = body.decode('ascii')
        obj = json.loads(text, object_pairs_hook=unique_object,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             ProtocolError('Nonfinite JSON value')))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ProtocolError('Invalid receipt JSON') from error
    require(type(obj) is dict, 'Receipt must be an object')
    return obj


class Session:
    def __init__(self, nonce, deadline_ns):
        require(type(nonce) is str and re.fullmatch('[0-9a-f]{32}', nonce),
                'Invalid session nonce')
        self.nonce = nonce
        self.deadline_ns = integer(deadline_ns)
        self.state = 'new'
        self.records = []
        self.captures = []
        self.receipts = []
        self.start_us = None
        self.last_host_ns = 0

    def _records(self, records, ordinal, stages):
        require(type(records) is list and len(records) == len(stages),
                'Stage cardinality mismatch')
        last = self.records[-1]['read_end_us'] if self.records else self.start_us
        for offset, (record, stage) in enumerate(zip(records, stages)):
            keys(record, RECORD_KEYS)
            exact(record['sequence'], len(self.records)+offset)
            exact(record['capture_ordinal'], ordinal)
            exact(record['stage'], stage)
            begin = integer(record['read_begin_us'])
            end = integer(record['read_end_us'])
            require(last <= begin <= end, 'Stage timestamp regression')
            integer(record['selector'], 0, 127)
            integer(record['bit23'], 0, 1)
            last = end
        require(len(self.records)+len(records) <= 81, 'Record capacity exceeded')

    def consume(self, line, host_start_ns, host_end_ns, *, data=None):
        """data is (count, eight-lowerhex CRC, elapsed_us, actual payload bytes).

        The DATA header and entire payload must precede its capture receipt.
        Host brackets cover receipt reads and must be monotonic and in budget.
        A well-formed failed receipt is retained with state=failed, never success.
        """
        try:
            return self._consume(line, host_start_ns, host_end_ns, data)
        except ProtocolError:
            self.state = 'failed'
            raise

    def _consume(self, line, host_start_ns, host_end_ns, data):
        require(self.state in ('new', 'armed'), 'Session already terminal')
        start = integer(host_start_ns)
        end = integer(host_end_ns)
        require(self.last_host_ns <= start <= end < self.deadline_ns,
                'Host bracket regression or acquisition deadline')
        obj = parse_line(line)
        require(COMMON <= set(obj), 'Missing common receipt fields')
        exact(obj['schema'], 1)
        exact(obj['nonce'], self.nonce)
        exact(obj['revision'], REVISION)
        kind = obj['kind']
        require(type(kind) is str, 'Invalid receipt kind')
        if kind == 'config':
            keys(obj, COMMON | {'profile', 'settings', 'rate_hz', 'bits',
                 'samples', 'captures', 'record_limit', 'start_us', 'records'})
            require(self.state == 'new' and data is None, 'Unexpected config')
            exact(obj['profile'], PROFILE)
            keys(obj['settings'], SETTINGS)
            for key, value in SETTINGS.items():
                exact(obj['settings'][key], value)
            for key, value in dict(rate_hz=16000000, bits=10, samples=16380,
                                   captures=20, record_limit=81).items():
                exact(obj[key], value)
            self.start_us = integer(obj['start_us'])
            self._records(obj['records'], None, ('post_settings',))
            self.records.extend(obj['records'])
            self.state = 'armed'
        elif kind == 'capture':
            keys(obj, COMMON | {'capture_ordinal', 'completion',
                 'returned_samples', 'payload_bytes', 'payload_crc32',
                 'capture_elapsed_us', 'records'})
            require(self.state == 'armed' and len(self.captures) < 20,
                    'Unexpected capture receipt')
            exact(obj['capture_ordinal'], len(self.captures))
            exact(obj['completion'], True)
            exact(obj['returned_samples'], 16380)
            exact(obj['payload_bytes'], 40950)
            integer(obj['capture_elapsed_us'])
            require(type(data) is tuple and len(data) == 4,
                    'Capture lacks its DATA frame')
            count, crc, elapsed, payload = data
            exact(count, 16380)
            exact(elapsed, obj['capture_elapsed_us'])
            require(type(payload) is bytes and len(payload) == 40950,
                    'Incomplete DATA payload')
            require(type(crc) is str and re.fullmatch('[0-9a-f]{8}', crc),
                    'Invalid DATA CRC field')
            exact(obj['payload_crc32'], crc)
            require(zlib.crc32(payload) == int(crc, 16), 'DATA CRC mismatch')
            self._records(obj['records'], len(self.captures), STAGES)
            self.records.extend(obj['records'])
            self.captures.append(obj)
        elif kind == 'end':
            keys(obj, COMMON | {'status', 'captures', 'pairs', 'payload_bytes',
                 'record_count', 'start_us', 'end_us'})
            require(self.state == 'armed' and data is None and
                    len(self.captures) == 20 and len(self.records) == 81,
                    'Early terminal receipt')
            for key, value in dict(status='completed', captures=20, pairs=327600,
                                   payload_bytes=819000, record_count=81,
                                   start_us=self.start_us).items():
                exact(obj[key], value)
            stop = integer(obj['end_us'])
            require(self.records[-1]['read_end_us'] <= stop and
                    stop-self.start_us <= 30000000, 'Firmware deadline or time order')
            self.state = 'completed'
        elif kind == 'failed':
            keys(obj, COMMON | {'failure_kind', 'capture_ordinal', 'completion',
                 'returned_samples', 'capture_elapsed_us', 'records'})
            require(type(obj['failure_kind']) is str and obj['failure_kind'] in FAILURES,
                    'Unknown failure kind')
            ordinal = obj['capture_ordinal']
            if ordinal is not None:
                require(self.state == 'armed', 'Acquisition before configuration')
                exact(ordinal, len(self.captures))
                integer(ordinal, 0, 19)
            else:
                require(all(obj[key] is None for key in
                            ('completion', 'returned_samples', 'capture_elapsed_us')),
                        'Acquisition fields without an attempt')
            require(obj['completion'] is None or type(obj['completion']) is bool,
                    'Invalid completion field')
            for key in ('returned_samples', 'capture_elapsed_us'):
                if obj[key] is not None:
                    integer(obj[key], maximum=32767 if key == 'returned_samples' else (1 << 63)-1)
            records = obj['records']
            require(type(records) is list and len(records) <= 4,
                    'Invalid failure stage prefix')
            require(self.state == 'armed' or not records,
                    'Stages before session configuration')
            if data is not None:
                require(self.state == 'armed' and type(data) is tuple and
                        len(data) == 4 and ordinal is not None and len(records) == 4,
                        'Failed receipt lacks complete DATA context')
                count, crc, elapsed, payload = data
                exact(obj['completion'], True)
                exact(count, 16380)
                exact(obj['returned_samples'], count)
                exact(elapsed, obj['capture_elapsed_us'])
                require(type(crc) is str and re.fullmatch('[0-9a-f]{8}', crc) and
                        type(payload) is bytes and len(payload) == 40950 and
                        zlib.crc32(payload) == int(crc, 16),
                        'Failed receipt follows invalid DATA frame')
            if records:
                require(ordinal is not None, 'Stages lack a capture ordinal')
                self._records(records, ordinal, STAGES[:len(records)])
                self.records.extend(records)
            self.state = 'failed'
        else:
            raise ProtocolError('Unknown receipt kind')
        self.last_host_ns = end
        self.receipts.append(dict(receipt=obj, host_start_ns=start, host_end_ns=end))
        return obj
