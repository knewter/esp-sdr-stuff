#!/usr/bin/env python3
"""Bounded regobs-v1 acquisition worker; no installation or restoration.

Only the preservation/restoration supervisor may launch a real hardware trial.
Raw UART and IQ remain private. Diagnostics are read after entire binary frames.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import time
import zlib

import esp_register_receipts as protocol
from demo_esp_sdr import defer_spawn_cancellation
from esp_gain_state_probe import (AcquisitionDeadline, BudgetPort as BaseBudgetPort, ProbeCancelled,
                                  absolute_timer, persist, publish)
from esp_sdr_capture import STABLE_PORT, open_board, synchronize

ROOT = Path(__file__).resolve().parents[1]
SECONDS = 30
SAMPLES = 16380
SIZE = 40950


class BudgetPort(BaseBudgetPort):
    def write(self, data):
        remaining = self.remaining()
        original = self.port.write_timeout
        self.port.write_timeout = min(.25, remaining,
                                      original if original is not None else remaining)
        try:
            result = self.port.write(data)
        finally:
            self.port.write_timeout = original
        self.remaining()
        return result


def utc():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def private_path(path):
    path = path.resolve()
    protocol.require(not path.exists() and path.is_relative_to(ROOT/'.scratch') and
                     path != ROOT/'.scratch', 'Capture path must be fresh private scratch')
    protocol.require(subprocess.run(['git','-C',str(ROOT),'check-ignore','--quiet',str(path)],
                                   capture_output=True).returncode == 0,
                     'Capture path must be ignored')
    path.mkdir(parents=True, mode=0o700)
    return path


def read_line(port):
    bracket = dict(host_start_ns=time.monotonic_ns(), host_start_utc=utc())
    raw = bytearray()
    while len(raw) < 2048:
        chunk = port.read(1)
        if not chunk:
            continue
        raw.extend(chunk)
        if chunk == b'\n':
            bracket.update(host_end_ns=time.monotonic_ns(), host_end_utc=utc())
            return bytes(raw), bracket
    raise protocol.ProtocolError('Protocol line budget exceeded')


def request(port, text):
    start = time.monotonic_ns()
    data = (text+'\n').encode('ascii')
    protocol.require(port.write(data) == len(data), 'Incomplete command write')
    port.flush()
    raw, bracket = read_line(port)
    bracket['command_start_ns'] = start
    return raw, bracket


def receipt(session, line, bracket, data=None):
    obj = session.consume(line, bracket['host_start_ns'], bracket['host_end_ns'], data=data)
    session.receipts[-1].update({key:bracket[key] for key in
                                ('host_start_utc','host_end_utc')})
    return obj


def response(session, port, line, bracket, data=None):
    if line.startswith(b'ERR REGOBS1 '):
        match = re.fullmatch(rb'ERR REGOBS1 ([a-z_]+)\n', line)
        protocol.require(match is not None and match[1].decode() in protocol.FAILURES,
                         'Invalid diagnostic error framing')
        typed, typed_bracket = read_line(port)
        obj = protocol.parse_line(typed)
        protocol.exact(obj.get('kind'), 'failed')
        protocol.exact(obj.get('failure_kind'), match[1].decode())
        receipt(session, typed, typed_bracket, data)
        raise protocol.ProtocolError('Firmware diagnostic session failed')
    protocol.require(protocol.parse_line(line).get('kind') != 'failed',
                     'Failure lacks its fixed ERR prefix')
    return receipt(session, line, bracket, data)


def limits(line):
    protocol.require(line.startswith(b'LIMITS ') and line.endswith(b'\n'),
                     'Malformed limits reply')
    try:
        data = json.loads(line[7:].decode('ascii'), object_pairs_hook=protocol.unique_object)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise protocol.ProtocolError('Invalid limits JSON') from error
    protocol.keys(data, {'gain','bandwidth','rates','bits'})
    protocol.require(all(type(v) is list and v and all(type(n) is int for n in v)
                         for v in data.values()), 'Invalid limits types')
    gain, bw = data['gain'], data['bandwidth']
    protocol.require(len(gain) == 3 and gain[0] == 0 and 48 <= gain[1] <= 127 and
                     gain[2] == 1 and len(bw) == 4 and
                     0 <= bw[0] <= 20 <= bw[1] <= 100 and bw[2:] == [1,0] and
                     sorted(data['rates']) == [16000000,40000000,80000000] and
                     sorted(data['bits']) == [8,10], 'Fixed profile unavailable')
    return data


def capture(port, session, rows, payloads):
    line, bracket = request(port, 'CAP20 16380 6')
    if line.startswith(b'ERR REGOBS1 '):
        response(session, port, line, bracket)
    match = re.fullmatch(rb'DATA ([0-9]+) ([0-9a-f]{8}) ([0-9]+)\n', line)
    protocol.require(match is not None, 'Invalid DATA header')
    count, crc, elapsed = int(match[1]), match[2].decode(), int(match[3])
    protocol.exact(count, SAMPLES)
    protocol.integer(elapsed)
    payload = bytearray()
    payloads.append(payload)
    row = dict(capture_ordinal=len(rows), returned_samples=count, payload_crc32=crc,
               capture_elapsed_us=elapsed, status='failed', header_bracket=bracket)
    rows.append(row)
    while len(payload) < SIZE:
        chunk = port.read(SIZE-len(payload))
        if chunk:
            payload.extend(chunk)
    row.update(payload_received_ns=time.monotonic_ns(), payload_received_utc=utc(),
               payload_bytes=len(payload), crc_ok=zlib.crc32(payload) == int(crc,16))
    protocol.require(row['crc_ok'], 'DATA CRC mismatch')
    line, bracket = read_line(port)
    obj = response(session, port, line, bracket,
                   (count,crc,elapsed,bytes(payload)))
    protocol.exact(obj['kind'], 'capture')
    row.update(status='completed', receipt_bracket=bracket)


def run(private, port_name=STABLE_PORT):
    private = private_path(private)
    nonce = secrets.token_hex(16)
    result = dict(schema=1, kind=protocol.PROFILE, revision=protocol.REVISION,
                  status='failed', requested_captures=20, acquisition_ceiling_seconds=SECONDS,
                  source_controlled=False, raw_bytes_private=True, captures=[],
                  restoration_performed=False, transmitted_event_count=None,
                  calibrated_gain_proven=False, SDR_decoding_proven=False)
    port = budget = session = None
    payloads = []
    start_ns = None
    cleaning = cancelled = False
    handlers = {s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    def cancel(*_):
        nonlocal cancelled
        if cancelled:
            return
        cancelled = True
        if not cleaning:
            raise ProbeCancelled('Register observation cancelled')
    for sig in handlers:
        signal.signal(sig, cancel)
    try:
        try:
            with defer_spawn_cancellation():
                port = open_board(port_name, baud=921600, timeout=.25)
                start_ns = time.monotonic_ns()
            deadline_ns = start_ns+int(SECONDS*1000000000)
            result.update(acquisition_start_ns=start_ns, acquisition_start_utc=utc())
            budget = BudgetPort(port, deadline_ns/1000000000)
            session = protocol.Session(nonce, deadline_ns)
            with absolute_timer(budget.remaining(), budget):
                synchronize(budget, seconds=min(5, budget.remaining()))
                query_results = {}
                for query in ('INFO','LIMITS?','BAUD?'):
                    line, bracket = request(budget, query)
                    if query == 'INFO':
                        protocol.exact(line, (protocol.INFO+'\n').encode())
                        parsed = protocol.INFO
                    elif query == 'BAUD?':
                        protocol.exact(line, b'BAUD 921600\n')
                        parsed = 'BAUD 921600'
                    else:
                        parsed = limits(line)
                    query_results[query] = dict(parsed=parsed, bracket=bracket)
                result['queries'] = query_results
                result['setting_brackets'] = {}
                for setting in ('FREQ 2401','BANDWIDTH 20','GAIN MANUAL 48'):
                    line, bracket = request(budget, setting)
                    protocol.exact(line, b'OK\n')
                    result['setting_brackets'][setting] = bracket
                line, bracket = request(budget, 'REGOBS1 BEGIN '+nonce)
                obj = response(session, budget, line, bracket)
                protocol.exact(obj['kind'], 'config')
                for _ in range(20):
                    capture(budget, session, result['captures'], payloads)
                line, bracket = request(budget, 'REGOBS1 END '+nonce)
                obj = response(session, budget, line, bracket)
                protocol.exact(obj['kind'], 'end')
                protocol.require(session.state == 'completed', 'Missing terminal completion')
                budget.remaining()
                result['status'] = 'completed'
        except BaseException as error:
            result['error_kind'] = type(error).__name__
        finally:
            cleaning = True
            if start_ns is not None:
                end_ns = time.monotonic_ns()
                result.update(acquisition_end_ns=end_ns, acquisition_end_utc=utc(),
                              acquisition_elapsed_seconds=(end_ns-start_ns)/1000000000)
            if port is not None:
                try:
                    port.close()
                    result['uart_closed'] = getattr(port,'is_open',None) is False
                except Exception as error:
                    result.update(uart_closed=False, uart_close_error_kind=type(error).__name__)
            else:
                result['uart_closed'] = True
        result.update(cancelled=cancelled, verified_capture_count=len(session.captures) if session else 0,
                      records=session.records if session else [], receipts=session.receipts if session else [])
        if cancelled or not result['uart_closed'] or result.get('acquisition_elapsed_seconds',SECONDS+1) >= SECONDS:
            result['status'] = 'failed'
        wire = bytes(budget.wire) if budget else b''
        result.update(consumed_uart_bytes=budget.received_bytes if budget else 0,
                      retained_wire_bytes=len(wire), retained_wire_sha256=hashlib.sha256(wire).hexdigest(),
                      wire_scope='Host-buffered bytes only; interruption may leave an unobserved final kernel-read boundary')
        if result['consumed_uart_bytes'] != len(wire):
            result['status'] = 'failed'
        if not result['uart_closed']:
            result['wire_persistence'] = dict(verified=False,error_kind='UartClosureUnconfirmed')
        else:
            try:
                result['wire_persistence'] = persist(private/'wire.bin',wire)
            except Exception as error:
                result.update(status='failed',wire_persistence=dict(verified=False,error_kind=type(error).__name__))
        for index,(payload,row) in enumerate(zip(payloads,result['captures'])):
            data = bytes(payload)
            row.update(retained_payload_bytes=len(data), retained_payload_sha256=hashlib.sha256(data).hexdigest())
            if not result['uart_closed']:
                row['payload_persistence'] = dict(verified=False,error_kind='UartClosureUnconfirmed')
            else:
                try:
                    row['payload_persistence'] = persist(private/f'iq-{index:02d}.bin',data)
                except Exception as error:
                    row['payload_persistence'] = dict(verified=False,error_kind=type(error).__name__)
                    result['status'] = 'failed'
        result['cancelled'] = cancelled
        if cancelled:
            result['status'] = 'failed'
        if result['uart_closed']:
            publish(private/'capture.json', result)
        else:
            # The supervisor captures terminal metadata in RAM, confirms the
            # entire worker group exited, then persists this failed receipt.
            # Neither raw buffers nor metadata are written by an unclosed worker.
            result['capture_receipt_persisted'] = False
        return result
    finally:
        for sig,handler in handlers.items():
            signal.signal(sig, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private',type=Path,required=True)
    parser.add_argument('--port',default=STABLE_PORT,choices=[STABLE_PORT])
    args = parser.parse_args(argv)
    old = os.umask(0o077)
    try:
        result = run(args.private,args.port)
        print(json.dumps(result),flush=True)
        return 0 if result['status']=='completed' else 2
    finally:
        os.umask(old)


if __name__ == '__main__':
    raise SystemExit(main())
