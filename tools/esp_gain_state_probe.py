#!/usr/bin/env python3
"""Fixed-profile 20-snapshot gain-state diagnostic; exclusive operator only.

No flashing, restoration, source control, settings retries or decoder changes.
The caller must separately verify preservation/installation and restore afterward.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import zlib

from demo_esp_sdr import defer_spawn_cancellation
from esp_sdr_capture import STABLE_PORT, open_board, synchronize, numerical_stats

ROOT = Path(__file__).resolve().parents[1]
COUNT = 20
SECONDS = 30
WIRE_LIMIT = 2 * 1024 * 1024
SAMPLES = 16380
PAYLOAD_BYTES = 40950
PROFILE = dict(frequency_mhz=2401, bandwidth_mhz=20, gain_mode='MANUAL',
               gain_index=48, nominal_rate_hz=16000000, bits_per_component=10,
               samples=SAMPLES, baud=921600)


class ProbeError(RuntimeError): pass
class AcquisitionDeadline(ProbeError): pass
class ProbeCancelled(ProbeError): pass


@contextmanager
def absolute_timer(seconds, budget):
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise ProbeError('An existing process alarm prevents an independent acquisition deadline')
    previous = signal.getsignal(signal.SIGALRM)
    def expire(*unused):
        if budget.expired: return
        budget.expired=True
        raise AcquisitionDeadline('Absolute acquisition budget exhausted')
    signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class BudgetPort:
    """Capture consumed bytes and bound reads, including startup synchronization."""
    def __init__(self, port, deadline):
        self.port = port; self.deadline = deadline
        self.wire = bytearray(); self.received_bytes = 0; self.expired = False

    @property
    def timeout(self): return self.port.timeout
    @timeout.setter
    def timeout(self, value): self.port.timeout = value

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            # Retiring the timer before unwinding prevents a second pending alarm
            # from interrupting retention of the first deadline failure.
            self.expired=True
            signal.setitimer(signal.ITIMER_REAL,0)
            raise AcquisitionDeadline('Absolute acquisition budget exhausted')
        return remaining

    def write(self, data): self.remaining(); return self.port.write(data)
    def flush(self): self.remaining(); return self.port.flush()

    def read(self, size):
        remaining = self.remaining(); original = self.port.timeout
        self.port.timeout = min(.25, remaining, original if original is not None else remaining)
        try: chunk = self.port.read(size)
        finally: self.port.timeout = original
        self.received_bytes += len(chunk)
        if len(self.wire) + len(chunk) > WIRE_LIMIT:
            # The over-limit chunk is retained too; each requested read is bounded
            # by one40950-byte payload. Fail immediately, never continue growing.
            self.wire.extend(chunk)
            raise ProbeError('Consumed wire budget exceeded')
        self.wire.extend(chunk)
        self.remaining()
        return chunk


def line(port):
    start = time.monotonic_ns(); data = bytearray()
    while len(data) < 256:
        chunk = port.read(1)
        if not chunk: continue
        data.extend(chunk)
        if chunk == b'\n':
            end = time.monotonic_ns()
            try: value = bytes(data).decode('ascii').strip()
            except UnicodeError as error: raise ProbeError('Non-ASCII protocol reply') from error
            return value, {'host_line_start_ns': start, 'host_line_end_ns': end}
    raise ProbeError('Protocol line budget exceeded')


def request(port, text):
    start = time.monotonic_ns(); port.write((text+'\n').encode('ascii')); port.flush()
    reply, bracket = line(port)
    return reply, {'command_start_ns': start, **bracket}


def gain(port, stage, index=None):
    reply, bracket = request(port, 'GAIN?')
    match = re.fullmatch(r'GAIN (HARDWARE|MANUAL) (-?\d+) 0 (\d+) ([01])', reply)
    if not match: raise ProbeError('Malformed gain reply')
    mode, code, maximum, bit = match.groups(); code=int(code); maximum=int(maximum)
    if not 0 <= maximum <= 127 or (mode=='HARDWARE' and code!=-1) or (mode=='MANUAL' and not 0<=code<=maximum):
        raise ProbeError('Invalid gain field bounds')
    return dict(stage=stage, capture_index=index, software_mode=mode, software_gain_index=code,
                declared_minimum=0, startup_gain_maximum=maximum, observed_register_bit23=int(bit),
                expected_software_profile=(mode=='MANUAL' and code==48 and maximum>=48),
                observed_manual_enable_bit_set=(bit=='1'), **bracket)


def capture(port, index):
    reply, bracket = request(port, 'CAP20 16380 6')
    row = dict(capture_index=index, **bracket, status='in_progress')
    match = re.fullmatch(r'DATA (\d+) ([0-9a-fA-F]{8}) (\d+)', reply)
    if not match: raise ProbeError('Malformed capture header')
    count, expected, elapsed = int(match[1]), int(match[2],16), int(match[3])
    if not 256<=count<=SAMPLES: raise ProbeError('Unsafe capture count')
    size=(count*20+7)//8
    row.update(returned_samples=count,expected_crc32=f'{expected:08x}',firmware_capture_us=elapsed,
               declared_payload_bytes=size)
    payload=bytearray()
    try:
        while len(payload)<size:
            chunk=port.read(size-len(payload))
            if chunk: payload.extend(chunk)
    except BaseException as error:
        row.update(status='failed',error_kind=type(error).__name__)
        raise PartialCapture(bytes(payload),row) from error
    payload=bytes(payload); actual=zlib.crc32(payload)
    valid=(count==SAMPLES and size==PAYLOAD_BYTES and actual==expected)
    row.update(returned_samples=count, payload_bytes=len(payload), expected_crc32=f'{expected:08x}',
               actual_crc32=f'{actual:08x}', firmware_capture_us=elapsed,
               payload_received_ns=time.monotonic_ns(),crc_ok=actual==expected,
               sample_count_ok=count==SAMPLES,expected_length_ok=len(payload)==PAYLOAD_BYTES,
               integrity_valid=valid,status='completed' if valid else 'integrity_failed',
               nominal_rf_window_us=count/16000000*1e6)
    return payload,row


class PartialCapture(ProbeError):
    def __init__(self,payload,row): self.payload=payload; self.row=row


def paths(private, output):
    private=private.resolve(); output=output.resolve()
    if (private.exists() or not any(private.is_relative_to(ROOT/root) and private!=ROOT/root for root in ('.scratch','backups'))
            or subprocess.run(['git','-C',str(ROOT),'check-ignore','--quiet',str(private)],capture_output=True).returncode):
        raise ProbeError('Private path must be fresh and ignored inside this repository')
    if output.exists() or not output.is_relative_to(ROOT/'docs/evidence') or output==ROOT/'docs/evidence':
        raise ProbeError('Public output must be a fresh repository evidence directory')
    private.mkdir(parents=True,mode=0o700); output.mkdir(parents=True)
    return private,output


def persist(path, data):
    with path.open('xb') as stream: stream.write(data)
    path.chmod(0o600)
    saved=path.read_bytes()
    if saved!=data: raise OSError('Private byte persistence differs')
    return dict(saved_bytes=len(saved),saved_sha256=hashlib.sha256(saved).hexdigest(),verified=True)


def publish(path, record):
    temporary=path.with_suffix('.tmp'); temporary.write_text(json.dumps(record,indent=2)+'\n'); temporary.replace(path)


def run(private, output):
    private,output=paths(private,output)
    record=dict(schema=1,kind='bounded fixed-profile gain-state diagnostic',profile=PROFILE,
                requested_captures=COUNT,acquisition_ceiling_seconds=SECONDS,status='failed',
                source_controlled=False,restoration_performed=False,
                restoration_requirement='Caller must close owned groups and verify original full-image restoration',
                gain_readback_limit='Mode/index and maximum are software/startup state; only register bit23 is read live. No live gain index or calibrated dB.',
                capture_clock_limit='Nominal RF windows; full host reply brackets are not synchronized RF packet timestamps',
                queries={},setting_replies={},gain_observations=[],captures=[])
    port=None; budget=None; payloads=[]; cleaning=False; cancelled=False
    handlers={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    def cancel(*unused):
        nonlocal cancelled
        if cancelled: return
        cancelled=True
        if not cleaning: raise ProbeCancelled('Operator cancellation')
    for sig in handlers: signal.signal(sig,cancel)
    try:
        try:
            # Ownership assignment is protected before deferred cancellation is replayed.
            with defer_spawn_cancellation(): port=open_board(STABLE_PORT,baud=921600,timeout=.25)
            start=time.monotonic(); record['acquisition_start_ns']=time.monotonic_ns()
            budget=BudgetPort(port,start+SECONDS)
            with absolute_timer(budget.remaining(),budget):
                synchronize(budget,seconds=min(5,budget.remaining()))
                for query in ('INFO','LIMITS?','BAUD?'):
                    reply,bracket=request(budget,query)
                    if query=='INFO' and reply!='ESP32SDR 6 burst 16380': raise ProbeError('Unexpected receiver protocol')
                    if query=='BAUD?' and reply!='BAUD 921600': raise ProbeError('Unexpected receiver baud')
                    if query=='LIMITS?':
                        if not reply.startswith('LIMITS '): raise ProbeError('Malformed limits')
                        limits=json.loads(reply[7:])
                        if (type(limits) is not dict or set(limits)!={'rates','bits','gain','bandwidth'} or
                                any(type(v) is not list or not v or any(type(n) is not int for n in v) for v in limits.values()) or
                                len(limits['gain'])!=3 or len(limits['bandwidth'])!=4 or
                                limits['gain'][0]!=0 or not 48<=limits['gain'][1]<=127 or limits['gain'][2]!=1 or
                                not limits['bandwidth'][0]<=20<=limits['bandwidth'][1] or
                                not 0<=limits['bandwidth'][0]<=limits['bandwidth'][1]<=100 or
                                limits['bandwidth'][2:]!=[1,0] or
                                set(limits['rates'])!={16000000,40000000,80000000} or set(limits['bits'])!={8,10}):
                            raise ProbeError('Required fixed profile unavailable')
                        record['queries'][query]={'parsed_limits':limits,**bracket}
                    else: record['queries'][query]={'reply':reply,**bracket}
                for setting in ('FREQ 2401','BANDWIDTH 20','GAIN MANUAL 48'):
                    reply,bracket=request(budget,setting)
                    if reply!='OK': raise ProbeError('Fixed setting rejected')
                    record['setting_replies'][setting]={'reply':'OK',**bracket}
                record['gain_observations'].append(gain(budget,'after_settings'))
                for index in range(COUNT):
                    record['gain_observations'].append(gain(budget,'before_capture',index))
                    record['last_attempted_capture_index']=index
                    try: payload,row=capture(budget,index)
                    except PartialCapture as error:
                        payloads.append(error.payload);record['captures'].append(error.row);raise
                    payloads.append(payload);record['captures'].append(row)
                    record['gain_observations'].append(gain(budget,'after_capture',index))
                budget.remaining()
                record['status']='completed'
        except BaseException as error:
            record['error_kind']=type(error.__cause__).__name__ if isinstance(error,PartialCapture) and error.__cause__ else type(error).__name__
        finally:
            cleaning=True
            if budget: record['acquisition_elapsed_seconds']=time.monotonic()-start
            if port:
                try: port.close();record['uart_closed']=not bool(getattr(port,'is_open',False))
                except Exception as error: record['uart_closed']=False;record['uart_close_error_kind']=type(error).__name__
            else: record['uart_closed']=True
        record['capture_count']=len(record['captures'])
        record['integrity_valid_count']=sum(row.get('integrity_valid',False) for row in record['captures'])
        record['expected_software_state_all_observed']=bool(record['gain_observations']) and all(row['expected_software_profile'] for row in record['gain_observations'])
        record['manual_enable_bit_all_observed_set']=bool(record['gain_observations']) and all(row['observed_manual_enable_bit_set'] for row in record['gain_observations'])
        if (record['capture_count']!=COUNT or record['integrity_valid_count']!=COUNT or
                not record['expected_software_state_all_observed'] or
                not record['uart_closed'] or record.get('acquisition_elapsed_seconds',SECONDS+1)>SECONDS): record['status']='failed'
        wire=bytes(budget.wire) if budget else b''
        record['consumed_uart_bytes']=budget.received_bytes if budget else 0
        record['private_wire_retained_bytes']=len(wire)
        record['consumed_bytes_all_buffered']=(record['consumed_uart_bytes']==len(wire))
        record['private_wire_scope']='Only bytes committed to the host buffer; interruption can leave an unobserved final kernel-read boundary'
        if not record['consumed_bytes_all_buffered']:record['status']='failed'
        record['private_wire_buffer_sha256']=hashlib.sha256(wire).hexdigest()
        try: record['private_wire_persistence']=persist(private/'wire.bin',wire)
        except Exception as error:
            record['private_wire_persistence']={'verified':False,'error_kind':type(error).__name__};record['status']='failed'
        for index,(payload,row) in enumerate(zip(payloads,record['captures'])):
            row['private_payload_sha256']=hashlib.sha256(payload).hexdigest();row['retained_payload_bytes']=len(payload)
            try: row['private_payload_persistence']=persist(private/f'iq-{index:02d}.bin',payload)
            except Exception as error:
                row['private_payload_persistence']={'verified':False,'error_kind':type(error).__name__};record['status']='failed'
            if row.get('integrity_valid'):
                try: row['numerical_stats']=numerical_stats(payload,SAMPLES,10)
                except Exception as error:
                    row['numerical_stats_error_kind']=type(error).__name__;record['status']='failed'
        record['cancelled']=cancelled
        if cancelled:record['status']='failed'
        publish(private/'results.json',record);publish(output/'results.json',record)
        return 0 if record['status']=='completed' else 2
    finally:
        for sig,handler in handlers.items(): signal.signal(sig,handler)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private',type=Path,required=True,help='Fresh ignored private bytes directory')
    parser.add_argument('--output',type=Path,required=True,help='Fresh sanitized docs/evidence directory')
    args=parser.parse_args(argv)
    previous=os.umask(0o077)
    try: return run(args.private,args.output)
    finally: os.umask(previous)


if __name__=='__main__': raise SystemExit(main())
