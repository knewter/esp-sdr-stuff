#!/usr/bin/env python3
"""Install the isolated register diagnostic, capture once, and verify restoration.

Run/restore are exclusive physical operations. Help and artifact checks do not
open hardware. Raw flash, UART, IQ and subprocess output stay private.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time

import demo_esp_sdr as lifecycle
import esp_register_artifact as artifact_guard
import esp_register_receipts as protocol
from esp_gain_state_probe import persist
from native_ble_reference import security_check

ROOT = Path(__file__).resolve().parents[1]
PIPE_LIMIT = 512 * 1024
WORKER_SECONDS = 60
CALLERS = ('esp_register_observation.py', 'esp_register_probe.py',
           'esp_register_receipts.py', 'esp_register_artifact.py',
           'build_esp_register_observation.py', 'build_esp_sdr_uart.py',
           'demo_esp_sdr.py', 'esp_sdr_capture.py', 'esp_sdr_spectrum_bridge.py',
           'flash_trial.py', 'esp_gain_state_probe.py', 'native_ble_reference.py',
           'build_native_ble_reference.py')


def committed_callers():
    revision = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'], text=True).strip()
    hashes = {}
    for name in CALLERS:
        relative = 'tools/'+name
        raw = (ROOT/relative).read_bytes()
        pinned = subprocess.check_output(['git','-C',str(ROOT),'show',revision+':'+relative])
        protocol.require(raw == pinned, 'Lifecycle dependencies must be committed before hardware')
        hashes[relative] = hashlib.sha256(raw).hexdigest()
    return dict(revision=revision, files=hashes)


def install(a):
    data, _ = artifact_guard.validate_artifact(a.artifact, a.manifest)
    lifecycle.identity_check(a.port)
    security_check()
    protocol.require(subprocess.run(['fuser',a.port],capture_output=True).returncode == 1,
                     'Serial target already has an operator')
    command = ['esptool','--chip','esp32','--port',a.port,'--baud','460800',
               'write-flash','--no-progress','--flash-mode','dio','--flash-freq','40m',
               '--flash-size','2MB']
    for part in data['parts']:
        command.extend((hex(part['offset']),str(a.artifact/'esp32'/part['name'])))
    lifecycle.execute(command, a.private/'install.log')


def drain(selector, buffers, timeout):
    """Read bounded bytes from both pipes without deadlocking either producer."""
    for key, _ in selector.select(timeout):
        raw = os.read(key.fd, 8192)
        if not raw:
            selector.unregister(key.fileobj)
            continue
        target = buffers[key.data]
        if len(target)+len(raw) > PIPE_LIMIT:
            target.extend(raw[:PIPE_LIMIT-len(target)])
            raise protocol.ProtocolError('Worker output exceeds its RAM limit')
        target.extend(raw)


def worker_process(command, private, seconds=WORKER_SECONDS):
    """Persist no parent worker output until its complete process group is gone."""
    proc = None
    buffers = {'stdout':bytearray(), 'stderr':bytearray()}
    selector = selectors.DefaultSelector()
    error = None
    code = None
    try:
        with lifecycle.defer_spawn_cancellation():
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    start_new_session=True)
        for name in buffers:
            stream = getattr(proc,name)
            os.set_blocking(stream.fileno(),False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = time.monotonic()+seconds
        while selector.get_map():
            protocol.require(time.monotonic() < deadline, 'Worker supervision deadline exhausted')
            drain(selector,buffers,min(.1,max(0,deadline-time.monotonic())))
        code = proc.wait(timeout=max(.001,deadline-time.monotonic()))
    except BaseException as caught:
        error = caught
    finally:
        try:
            lifecycle.stop_process(proc)
        except Exception as caught:
            selector.close()
            if proc is not None:
                proc.stdout.close(); proc.stderr.close()
            raise lifecycle.OwnedHardwareClosureError('Register worker group closure unconfirmed') from caught
        # A known-closed group cannot add more bytes. Retain an accessible
        # bounded pipe prefix even after cancellation/deadline/output failure.
        try:
            while selector.get_map():
                before = sum(map(len,buffers.values()))
                drain(selector,buffers,0)
                if sum(map(len,buffers.values())) == before and selector.get_map():
                    break
        except Exception as caught:
            if error is None: error = caught
        finally:
            selector.close()
            if proc is not None:
                proc.stdout.close(); proc.stderr.close()
    for name,raw in buffers.items():
        persist(private/('worker-'+name+'.bin'), bytes(raw))
    if error is not None:
        raise error
    return code, bytes(buffers['stdout'])


def file_receipt(path, expected_bytes, expected_sha):
    protocol.integer(expected_bytes)
    protocol.require(type(expected_sha) is str and len(expected_sha) == 64,
                     'Missing private buffer hash')
    protocol.require(path.is_file() and not path.is_symlink() and path.stat().st_mode&0o077 == 0,
                     'Saved buffer is not a private regular file')
    raw = path.read_bytes()
    protocol.require(len(raw) == expected_bytes and hashlib.sha256(raw).hexdigest() == expected_sha,
                     'Saved private buffer differs from its receipt')
    return raw


def bind_wire(wire, rows, receipts):
    """Bind accepted metadata to original framed bytes, never a regenerated CRC.

    Failed trailing bytes are retained but cannot become accepted receipts. A
    declared frame/payload must appear in order at the actual binary boundary.
    """
    position = 0
    accepted = []
    def line():
        nonlocal position
        end = wire.find(b'\n',position)
        protocol.require(end>=0 and end-position<2048,'Incomplete retained protocol line')
        raw = wire[position:end+1]
        position=end+1
        return raw
    def typed(raw, data=None):
        if raw.startswith(b'ERR REGOBS1 '):
            match=re.fullmatch(rb'ERR REGOBS1 ([a-z_]+)\n',raw)
            protocol.require(match is not None and match[1].decode() in protocol.FAILURES,
                             'Invalid retained error prefix')
            raw=line()
            obj=protocol.parse_line(raw)
            protocol.exact(obj.get('kind'),'failed')
            protocol.exact(obj.get('failure_kind'),match[1].decode())
        else:
            obj=protocol.parse_line(raw)
            protocol.require(obj.get('kind')!='failed','Retained failure lacks ERR prefix')
        protocol.require(len(accepted)<len(receipts),'Unexpected declared receipt count')
        protocol.exact(obj,receipts[len(accepted)]['receipt'])
        accepted.append((raw,data))
    if not receipts:
        return []
    # Startup UART includes synchronization and settings replies. The first
    # diagnostic line, rather than an arbitrary later matching substring, owns
    # the start of the separately identified protocol.
    while position<len(wire):
        raw=line()
        if raw.startswith((b'REGOBS1 ',b'ERR REGOBS1 ')):
            typed(raw)
            break
    protocol.require(accepted,'Diagnostic receipt missing from saved wire')
    for index,row in enumerate(rows):
        header=line()
        match=re.fullmatch(rb'DATA ([0-9]+) ([0-9a-f]{8}) ([0-9]+)\n',header)
        protocol.require(match is not None,'Declared DATA header absent from retained wire')
        count,crc,elapsed=int(match[1]),match[2].decode(),int(match[3])
        for actual,expected in ((count,row['returned_samples']),(crc,row['payload_crc32']),
                                (elapsed,row['capture_elapsed_us'])):
            protocol.exact(actual,expected)
        length=protocol.integer(row['retained_payload_bytes'],maximum=40950)
        raw=wire[position:position+length]
        protocol.require(len(raw)==length and hashlib.sha256(raw).hexdigest()==row['retained_payload_sha256'],
                         'Declared payload differs from retained wire boundary')
        position+=length
        if length<40950:
            protocol.require(index==len(rows)-1,'Capture after incomplete retained DATA')
            break
        if len(accepted)<len(receipts):
            expected=receipts[len(accepted)]['receipt']
            if expected.get('kind') in ('capture','failed') and expected.get('capture_ordinal')==index:
                typed(line(),(count,crc,elapsed,raw))
    # A terminal/failure without an acquisition attempt follows the last actual
    # capture. Failure suffixes rejected by the worker are never fabricated.
    while len(accepted)<len(receipts):
        typed(line())
    protocol.require(len(accepted)==len(receipts),'Retained receipt prefix incomplete')
    if receipts[-1]['receipt'].get('kind')=='end':
        protocol.require(position==len(wire),'Unexpected UART bytes after terminal completion')
    return accepted


def capture_summary(result, private, code):
    """Independently replay typed receipts and saved bytes before publication."""
    protocol.require(type(result) is dict, 'Missing worker terminal object')
    protocol.exact(result.get('kind'),protocol.PROFILE)
    protocol.exact(result.get('revision'),protocol.REVISION)
    start = protocol.integer(result['acquisition_start_ns'])
    end = protocol.integer(result['acquisition_end_ns'])
    protocol.require(start <= end, 'Invalid worker acquisition times')
    rows = result['captures']
    receipts = result['receipts']
    protocol.require(type(rows) is list and len(rows)<=20 and type(receipts) is list and len(receipts)<=22,
                     'Worker cardinality exceeds protocol bounds')
    summary = dict(schema=1,kind=protocol.PROFILE,revision=protocol.REVISION,status='failed',
                   worker_exit_code=code,acquisition_elapsed_ns=end-start,requested_captures=20,
                   verified_capture_count=0,records=[],receipts=[],payloads=[],
                   raw_bytes_private=True,source_controlled=False,SDR_decoding_proven=False,
                   calibrated_gain_proven=False,transmitted_event_count=None)
    wire_state = result.get('wire_persistence',{})
    wire_ok = False
    wire = None
    if wire_state.get('verified') is True:
        wire = file_receipt(private/'wire.bin',result['retained_wire_bytes'],result['retained_wire_sha256'])
        protocol.exact(result['consumed_uart_bytes'],len(wire))
        protocol.exact(wire_state['saved_bytes'],len(wire))
        protocol.exact(wire_state['saved_sha256'],hashlib.sha256(wire).hexdigest())
        summary['wire'] = dict(saved_bytes=len(wire),saved_sha256=hashlib.sha256(wire).hexdigest(),verified=True)
        wire_ok = True
    else:
        summary['wire'] = dict(verified=False)
    payloads = {}
    saved_all = True
    for index,row in enumerate(rows):
        protocol.require(type(row) is dict,'Invalid capture row')
        protocol.exact(row['capture_ordinal'],index)
        length = protocol.integer(row['retained_payload_bytes'],maximum=40950)
        crc_ok = False
        saved = row.get('payload_persistence',{}).get('verified') is True
        if saved:
            raw = file_receipt(private/f'iq-{index:02d}.bin',length,row['retained_payload_sha256'])
            protocol.exact(row['payload_persistence']['saved_bytes'],len(raw))
            protocol.exact(row['payload_persistence']['saved_sha256'],hashlib.sha256(raw).hexdigest())
            import zlib
            crc_ok = length==40950 and zlib.crc32(raw)==int(row['payload_crc32'],16)
            if crc_ok:
                payloads[index]=(row['returned_samples'],row['payload_crc32'],row['capture_elapsed_us'],raw)
        saved_all &= saved
        item=dict(capture_ordinal=index,retained_payload_bytes=length,saved_verified=saved,crc_ok=crc_ok)
        if saved: item['saved_sha256']=hashlib.sha256(raw).hexdigest()
        summary['payloads'].append(item)
    if not receipts:
        return summary
    if wire is None:
        # Never publish unbound stage metadata as independently verified.
        return summary
    observed = bind_wire(wire,rows,receipts)
    nonce = receipts[0]['receipt'].get('nonce')
    session = protocol.Session(nonce,start+30000000000)
    for entry,(original_line,data) in zip(receipts,observed):
        obj = entry['receipt']
        # Actual wire payload integrity is independent of persistence. The
        # final success gate separately requires every saved IQ file to match.
        session.consume(original_line,entry['host_start_ns'],entry['host_end_ns'],data=data)
        protocol.require(entry['host_start_ns']>=start and entry['host_end_ns']<=end,
                         'Receipt lies outside acquisition bracket')
    protocol.exact(result['records'],session.records)
    protocol.exact(result['verified_capture_count'],len(session.captures))
    summary.update(verified_capture_count=len(session.captures),records=session.records,receipts=session.receipts)
    if (code==0 and result.get('status')=='completed' and result.get('uart_closed') is True
            and result.get('cancelled') is False and session.state=='completed'
            and end-start<30000000000 and wire_ok and saved_all and len(rows)==20
            and len(payloads)==20):
        summary['status']='completed'
    return summary


def collect(a):
    directory = a.private/'capture'
    code, raw = worker_process([sys.executable,str(ROOT/'tools/esp_register_probe.py'),
                               '--port',a.port,'--private',str(directory)],a.private)
    try:
        result = json.loads(raw.decode('ascii'),object_pairs_hook=protocol.unique_object)
    except (ValueError,UnicodeError) as caught:
        raise protocol.ProtocolError('No valid worker terminal JSON') from caught
    # The worker JSON may be uncertain; retain it privately after group closure.
    lifecycle.write_json(a.private/'worker-terminal.json',result)
    return capture_summary(result,directory,code)


def run(a):
    callers = committed_callers()
    data = info = None
    if a.action=='run':
        data,info = artifact_guard.validate_artifact(a.artifact,a.manifest)
    baseline = lifecycle.baseline_check()
    security_check()
    lifecycle.identity_check(a.port)
    a.output,a.private = lifecycle.validate_paths(a.output,a.private)
    old = os.umask(0o077)
    a.private.mkdir(parents=True,mode=0o700)
    a.output.mkdir(parents=True)
    record = dict(schema=1,kind=protocol.PROFILE,status='failed',action=a.action,
                  started_utc=lifecycle.utc(),callers=callers,baseline_sha256=baseline['sha256'],
                  stable_usb_identity_verified=True,capture_status='not_started',
                  restoration_status='not_attempted',restore_policy='always after installation attempt',
                  transmitted_event_count=None,SDR_decoding_proven=False)
    if data is not None:
        record['artifact'] = dict(manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),
                                 build_info_sha256=data['build_info_sha256'],parts=data['parts'],
                                 source_commit=info['source_commit'],source_tree_sha256=info['source_tree_sha256'],
                                 idf_commit=info['idf_commit'],version=protocol.REVISION)
    attempted = a.action=='restore'
    closed = True
    cleaning = False
    handlers = {}
    def cancel(*_):
        if not cleaning: raise lifecycle.Cancelled('Register lifecycle cancelled')
    try:
        for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,cancel)
        if a.action=='run':
            lifecycle.current_baseline_check(a,baseline)
            protocol.exact(committed_callers()['files'],callers['files'])
            attempted = True
            install(a)
            record['capture_status']='in_progress'
            result = collect(a)
            lifecycle.write_json(a.output/'capture.json',result)
            record['capture_status']=result['status']
            protocol.require(result['status']=='completed','Register observation failed')
    except (Exception,KeyboardInterrupt) as caught:
        record['error_kind']=type(caught).__name__
        if record['capture_status']=='in_progress':record['capture_status']='failed'
        if isinstance(caught,lifecycle.OwnedHardwareClosureError):closed=False
        lifecycle.write_json(a.private/'failure.json',dict(error_kind=type(caught).__name__))
    finally:
        cleaning = True
        record['installation_attempted']=attempted if a.action=='run' else False
        record['owned_uart_worker_exit_confirmed']=closed
        if attempted and not closed:
            record['restoration_status']='blocked_owned_worker_not_closed'
        elif attempted:
            try:
                lifecycle.restore_verified(a,baseline)
                record['restoration_status']='verified'
            except Exception as caught:
                record['restoration_status']='failed'
                record['restore_error_kind']=type(caught).__name__
                if isinstance(caught,lifecycle.OwnedHardwareClosureError):
                    record['owned_uart_worker_exit_confirmed']=False
        if record['restoration_status']=='verified' and 'error_kind' not in record and (
                a.action=='restore' or record['capture_status']=='completed'):
            record['status']='completed'
        record['ended_utc']=lifecycle.utc()
        try:
            lifecycle.write_json(a.output/'register-observation.json',record)
        finally:
            for sig,handler in handlers.items():signal.signal(sig,handler)
            os.umask(old)
    print(json.dumps(dict(kind='REGISTER_OBSERVATION_CLOSED',status=record['status'],
                         restoration_status=record['restoration_status'])),flush=True)
    return 0 if record['status']=='completed' else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('run','restore'))
    parser.add_argument('--artifact',type=Path)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--private',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--port',default=lifecycle.STABLE_PORT,choices=[lifecycle.STABLE_PORT])
    args = parser.parse_args(argv)
    if args.action=='run' and (args.artifact is None or args.manifest is None):
        parser.error('Run requires the separately verified diagnostic artifact and manifest')
    (ROOT/'.scratch').mkdir(exist_ok=True)
    with (ROOT/'.scratch/esp-demo.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:parser.error('Another ESP operator owns the lifecycle lock')
        return run(args)


if __name__=='__main__':raise SystemExit(main())
