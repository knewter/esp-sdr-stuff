#!/usr/bin/env python3
"""Bounded native passive BLE source reference with verified original restoration.

Hardware-free help. No Bluetooth source control, SDR decoding or emitted-event
denominator. Only the exclusive, identity-selected operator may run this tool.
"""
import argparse
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import signal
import struct
import subprocess
import sys
import time

import demo_esp_sdr as lifecycle_helpers
from build_native_ble_reference import DISABLED_HIDDEN, KIND, PARTS, REQUIRED, ROOT, SDK, SDK_NIX_SOURCE_HASH, VERSION, sha, source_files, source_tree_hash, validate_config

CONFIG=dict(schema=1,kind='CONFIG',version=VERSION,completion_mode='application_cancel',scan_ms=90000,passive=True,
            filter_duplicates=False,interval_units=160,window_units=160,uart_baud=115200,
            owned_ad_hex='0fffffff4553502d5344522d4556414c')
BASE_KEYS={'schema','kind','version'}
AGG_KEYS=BASE_KEYS|{'nonce','sequence','interval_start_us','interval_end_us','owned_interval',
                   'owned_total','rssi_known','rssi_sum','rssi_min','rssi_max'}
ERROR_STAGES={'CRYPTO_SELFTEST','UART','NVS','NIMBLE','COMMAND','START_TIMEOUT','SCAN','SCAN_TIMEOUT','COUNTER_OR_RESET','CONTROLLER_RESET','UNEXPECTED_COMPLETE','SCAN_INACTIVE','SCAN_CANCEL','SCAN_STILL_ACTIVE','SCAN_TIME_OVERRUN'}


class ProtocolError(ValueError):pass


def require(condition,message):
    if not condition:raise ProtocolError(message)


def security_check():
    text=(ROOT/'docs/evidence/firmware-preservation/security.log').read_text()
    for field in ('ABS_DONE_0','ABS_DONE_1'):
        require(re.search(rf'^{field}\s+.*= False\s',text,re.M),'Secure boot must be verified disabled')
    require(re.search(r'^FLASH_CRYPT_CNT\s+.*= 0\s',text,re.M),'Flash encryption must be verified disabled')


def partition_check(data):
    require(len(data)==3072,'Native partition-table length')
    expected=[(1,2,0x9000,0x6000,b'nvs'),(1,1,0xf000,0x1000,b'phy_init'),(0,0,0x10000,0x100000,b'factory')]
    for n,fields in enumerate(expected):
        magic,kind,subtype,offset,size,label,flags=struct.unpack('<HBBII16sI',data[n*32:(n+1)*32])
        require(magic==0x50aa and flags==0 and (kind,subtype,offset,size,label.rstrip(b'\0'))==fields,'Unexpected native partition layout')
    require(data[96:112]==b'\xeb\xeb'+b'\xff'*14 and data[112:128]==hashlib.md5(data[:96]).digest(),
            'Native partition-table checksum')
    require(data[128:]==b'\xff'*(len(data)-128),'Unexpected extra native partition')


def validate_artifact(artifact,manifest):
    artifact=artifact.resolve();manifest=manifest.resolve()
    require(artifact.is_relative_to(ROOT/'.scratch') and manifest==artifact/'manifest.json',
            'Native artifacts must be private ignored .scratch outputs')
    for file in (artifact,manifest,artifact/'build-info.json',artifact/'sdkconfig'):
        require(file.resolve().is_relative_to(artifact),'Native provenance must remain inside its private artifact')
        require(file.stat().st_mode&0o077==0,'Native artifact/provenance permissions must be private')
    data=json.loads(manifest.read_text());info_path=manifest.with_name('build-info.json');info=json.loads(info_path.read_text())
    require(data.get('schema')==1 and data.get('kind')==info.get('kind')==KIND and
            data.get('target')==info.get('target')=='esp32' and data.get('version')==info.get('version')==VERSION,
            'Explicit native profile is required; SDR manifests are unsupported here')
    require(data.get('build_info_sha256')==sha(info_path),'Native build provenance hash mismatch')
    files=source_files();tree=source_tree_hash(files)
    require(info.get('source_files')==files and data.get('source_tree_sha256')==info.get('source_tree_sha256')==tree,
            'Native artifact differs from current committed source')
    require(re.fullmatch('[0-9a-f]{40}',info.get('source_commit','')),'Missing native source commit')
    for name,digest in files.items():
        committed=subprocess.check_output(['git','-C',str(ROOT),'show',
            info['source_commit']+':firmware/native-ble-reference/'+name])
        require(hashlib.sha256(committed).hexdigest()==digest,'Native source commit does not contain exact build inputs')
    # The exact current source files must be committed, not merely hashed.
    require(subprocess.run(['git','-C',str(ROOT),'diff','--quiet','HEAD','--','firmware/native-ble-reference'],
                           capture_output=True).returncode==0,'Native source changes must be committed')
    provenance=info.get('nix_sdk_provenance',{})
    require(info.get('idf_commit')==provenance.get('revision')==SDK and
            provenance.get('source_hash')==SDK_NIX_SOURCE_HASH and
            str(provenance.get('source_path','')).startswith('/nix/store/') and
            str(provenance.get('idf_path','')).startswith('/nix/store/'),'Unpinned native SDK')
    require(info.get('profile')=={k:CONFIG[k] for k in ('completion_mode','scan_ms','passive','filter_duplicates','interval_units','window_units','uart_baud')},'Unexpected native radio/runtime profile')
    require(info.get('sdkconfig_sha256')==sha(manifest.with_name('sdkconfig')),'Native generated config hash mismatch')
    validate_config(manifest.with_name('sdkconfig').read_text())
    require(info.get('required_sdkconfig_lines')==list(REQUIRED) and
            info.get('disabled_hidden_sdkconfig_keys')==list(DISABLED_HIDDEN),'Native config policy differs')
    require(len(data.get('parts',[]))==3,'Unexpected native part count')
    for part,(name,offset,end) in zip(data['parts'],PARTS):
        require(part.get('name')==name and part.get('offset')==offset and type(part.get('size')) is int
                and 0<part['size']<=end-offset,'Native part layout differs')
        file=artifact/'esp32'/name
        require(file.resolve().is_relative_to(artifact),'Native binaries must remain inside their private artifact')
        require(file.stat().st_mode&0o077==0,'Native binaries must remain private')
        require(file.stat().st_size==part['size'] and sha(file)==part.get('sha256'),'Native part hash/length differs')
        raw=file.read_bytes()
        if name=='partition-table.bin':partition_check(raw)
        else:
            from esptool.bin_image import ESP32FirmwareImage
            image=ESP32FirmwareImage(io.BytesIO(raw))
            require(image.checksum==image.calculate_checksum() and image.append_digest and
                    image.stored_digest==image.calc_digest,'Native binary checksum/digest mismatch')
            require(len(raw)>=24 and raw[0]==0xe9 and 1<=raw[1]<=16 and raw[2]==2 and raw[3]==0x20
                    and raw[12:14]==b'\0\0','Native binary target/flash header mismatch')
            if name=='native_ble_reference.bin':
                require(raw[32:36]==struct.pack('<I',0xabcd5432) and
                        raw[48:80].split(b'\0')[0]==VERSION.encode() and
                        raw[80:112].split(b'\0')[0]==b'native_ble_reference','Native application descriptor differs')
    return data,info


class Records:
    def __init__(self,nonce):
        require(re.fullmatch('[0-9a-f]{16}',nonce) is not None,'Nonce must be16 lowercase ASCII hex characters')
        self.nonce=nonce;self.config=False;self.ready=None;self.end=None;self.sequence=0;self.total=0;self.last_end=None;self.rows=[]

    def accept(self,data,start,end):
        require(type(data) is dict and type(start) is int and type(end) is int and start<=end,'Invalid full-line receive bracket')
        require(type(data.get('schema')) is int and data['schema']==1 and data.get('version')==VERSION,'Native schema/version differs')
        kind=data.get('kind')
        if kind=='ERROR':
            require(set(data)==BASE_KEYS|{'stage','code'} and data['stage'] in ERROR_STAGES and type(data['code']) is int,'Unexpected firmware error schema')
            raise ProtocolError('Native firmware initialization/runtime failed')
        if kind=='CONFIG':
            require(data==CONFIG and all(type(data[k]) is type(v) for k,v in CONFIG.items()) and self.ready is None,
                    'Unexpected native configuration/restart')
            self.config=True;return None
        require(self.config and data.get('nonce')==self.nonce,'Configuration/nonce not established')
        if kind=='READY':
            require(set(data)==BASE_KEYS|{'nonce','scan_start_us','scan_status'} and self.ready is None and
                    type(data['scan_start_us']) is int and data['scan_start_us']>=0 and
                    type(data['scan_status']) is int and data['scan_status']==0,
                    'Invalid repeated/failed scan readiness')
            self.last_end=data['scan_start_us'];self.ready={**data,'host_line_start_ns':start,'host_line_end_ns':end}
            return self.ready
        require(self.ready is not None and self.end is None and kind in ('AGG','END'),'Aggregate outside owned scan')
        keys=AGG_KEYS|({'completion_mode','cancel_status','scan_active_after_stop','elapsed_us','scan_ms'} if kind=='END' else set())
        require(set(data)==keys,'Unexpected aggregate fields; raw data must not be published')
        for key in ('sequence','interval_start_us','interval_end_us','owned_interval','owned_total','rssi_known','rssi_sum'):
            require(type(data[key]) is int,'Noninteger native statistic')
        require(data['sequence']==self.sequence+1 and data['interval_start_us']==self.last_end and
                data['interval_start_us']<=data['interval_end_us'],'Aggregate sequence/time gap or restart')
        require(0<=data['owned_interval']<=1000000 and data['owned_total']==self.total+data['owned_interval']
                and data['owned_total']<=1000000,'Owned cumulative report count is inconsistent')
        known=data['rssi_known'];require(0<=known<=data['owned_interval'],'RSSI count differs from owned reports')
        if known:
            require(type(data['rssi_min']) is int and type(data['rssi_max']) is int and
                    -127<=data['rssi_min']<=data['rssi_max']<=20 and
                    data['rssi_min']*known<=data['rssi_sum']<=data['rssi_max']*known,'Invalid uncalibrated RSSI aggregate')
        else:require(data['rssi_min'] is None and data['rssi_max'] is None and data['rssi_sum']==0,'Empty RSSI bucket must be null')
        if kind=='END':
            require(data['completion_mode']=='application_cancel' and type(data['cancel_status']) is int and data['cancel_status']==0 and
                    type(data['scan_active_after_stop']) is bool and data['scan_active_after_stop'] is False and
                    type(data['scan_ms']) is int and data['scan_ms']==90000 and
                    type(data['elapsed_us']) is int and data['elapsed_us']==data['interval_end_us']-self.ready['scan_start_us'] and
                    90000000<=data['elapsed_us']<=92000000,'Acknowledged application stop status/duration differs')
            require(end-self.ready['host_line_end_ns']>=88000000000,'Host observed scan is too short')
        row={**data,'host_line_start_ns':start,'host_line_end_ns':end}
        self.rows.append(row);self.sequence=data['sequence'];self.total=data['owned_total'];self.last_end=data['interval_end_us']
        if kind=='END':self.end=row
        return row


def private_path_check(path):
    path=path.resolve()
    require(any(path.is_relative_to(ROOT/name) and path!=ROOT/name for name in ('.scratch','backups')) and
            not path.exists(),'Raw UART output must be a fresh private ignored directory')
    require(subprocess.run(['git','-C',str(ROOT),'check-ignore','--quiet',str(path)],capture_output=True).returncode==0,
            'Raw UART output must be ignored by Git')
    return path


def capture(a):
    a.private=private_path_check(a.private)
    lifecycle_helpers.identity_check(a.port)
    a.private.mkdir(mode=0o700,parents=True,exist_ok=False)
    nonce=secrets.token_hex(8);records=Records(nonce);connection=None;buffer=bytearray();line_start=None
    status='failed';error_kind=None;raw_count=0;start=time.monotonic();sent=False
    try:
        with lifecycle_helpers.defer_spawn_cancellation():
            connection=lifecycle_helpers.open_board(a.port,115200,timeout=.1)
        with (a.private/'uart.bin').open('wb') as raw:
            while time.monotonic()-start<135:
                before=time.monotonic_ns();data=connection.read(256);after=time.monotonic_ns()
                raw_count+=len(data)
                require(raw_count<=2000000,'Private UART budget exceeded')
                require(raw.write(data)==len(data),'Private UART log short write')
                for value in data:
                    if line_start is None:line_start=before
                    if value!=10:
                        buffer.append(value);require(len(buffer)<=4096,'UART line budget exceeded');continue
                    line=bytes(buffer).rstrip(b'\r');buffer.clear();begin=line_start;line_start=None
                    if not line.startswith(b'{'):continue
                    record=json.loads(line.decode('ascii'));result=records.accept(record,begin,after)
                    if record['kind']=='CONFIG' and not sent:
                        connection.write(('START '+nonce+'\n').encode());connection.flush();sent=True
                    if record['kind']=='READY':
                        ready=a.private/'ready.json';temporary=ready.with_suffix('.tmp')
                        lifecycle_helpers.write_json(temporary,result);temporary.replace(ready)
                        print(json.dumps({'kind':'NATIVE_REFERENCE_READY','host_line_end_ns':result['host_line_end_ns']}),flush=True)
                    if records.end is not None:status='completed';break
                if records.end is not None:break
                if records.ready is None and time.monotonic()-start>35:raise ProtocolError('Native readiness deadline expired')
            require(records.end is not None,'Native terminal deadline expired')
    except (Exception,KeyboardInterrupt) as error:
        error_kind=type(error).__name__
        lifecycle_helpers.write_json(a.private/'failure.json',{'error_kind':error_kind,'error':str(error)})
    finally:
        if connection is not None:connection.close()
        raw_path=a.private/'uart.bin';saved_bytes=None;saved_hash=None;raw_verified=False;raw_error=None
        try:
            saved_bytes=raw_path.stat().st_size;saved_hash=sha(raw_path);raw_verified=True
        except OSError as error:
            raw_error=type(error).__name__
            status='failed';error_kind=error_kind or 'RawPersistenceError'
        if status=='completed' and (not raw_verified or saved_bytes!=raw_count):
            status='failed';error_kind='RawPersistenceError'
        receipt=dict(schema=1,kind=KIND,status=status,error_kind=error_kind,configuration=CONFIG if records.config else None,
                     readiness=records.ready,aggregates=records.rows,terminal=records.end,owned_received_reports=records.total,
                     uart_closed=True,received_uart_bytes=raw_count,saved_uart_bytes_private=saved_bytes,saved_uart_sha256=saved_hash,
                     saved_uart_file_verified=raw_verified,all_received_uart_bytes_saved=raw_verified and saved_bytes==raw_count,
                     raw_log_verification_error_kind=raw_error,
                     transmitted_event_count=None,independent_RF_reference=False,
                     limitations='Native controller-delivered owned reports only; nominal ESP time, uncalibrated RSSI and UART/controller latency; no SDR decoding, exact RF event times or transmitted denominator.')
        target=a.private/'capture.json';temporary=target.with_suffix('.tmp');lifecycle_helpers.write_json(temporary,receipt);temporary.replace(target)
    return 0 if status=='completed' else 2


def install(a,data):
    lifecycle_helpers.identity_check(a.port);security_check()
    if subprocess.run(['fuser',a.port],capture_output=True).returncode==0:raise RuntimeError('Serial device is already open')
    # Validate immediately before building this native-only command as well.
    validate_artifact(a.artifact,a.manifest)
    command=['esptool','--chip','esp32','--port',a.port,'--baud','460800','write-flash','--no-progress',
             '--flash-mode','dio','--flash-freq','40m','--flash-size','4MB']
    for part in data['parts']:command.extend((hex(part['offset']),str(a.artifact/'esp32'/part['name'])))
    lifecycle_helpers.execute(command,a.private/'install.log')


def collect(a):
    proc=None;notified=False
    try:
        with (a.private/'capture-worker.log').open('wb') as log:
            with lifecycle_helpers.defer_spawn_cancellation():
                proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'_capture','--port',a.port,
                    '--private',str(a.private/'scanner')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            deadline=time.monotonic()+145
            while proc.poll() is None:
                ready=a.private/'scanner/ready.json'
                if ready.exists() and not notified:
                    value=json.loads(ready.read_text());print(json.dumps({'kind':'NATIVE_REFERENCE_READY','host_line_end_ns':value['host_line_end_ns']}),flush=True);notified=True
                if time.monotonic()>deadline:raise RuntimeError('Owned native worker deadline expired')
                time.sleep(.1)
            if proc.returncode:raise RuntimeError('Native worker failed; inspect private receipt')
    finally:
        try:lifecycle_helpers.stop_process(proc)
        except Exception as error:raise lifecycle_helpers.OwnedHardwareClosureError('Native UART worker group closure unconfirmed') from error
    return json.loads((a.private/'scanner/capture.json').read_text())


def run(a):
    baseline=lifecycle_helpers.baseline_check();security_check();lifecycle_helpers.identity_check(a.port)
    data=info=None
    if a.action=='run':data,info=validate_artifact(a.artifact,a.manifest)
    a.output,a.private=lifecycle_helpers.validate_paths(a.output,a.private)
    old_umask=os.umask(0o077);a.private.mkdir(mode=0o700,parents=True);a.output.mkdir(parents=True)
    record=dict(schema=1,kind=KIND,started_utc=lifecycle_helpers.utc(),status='failed',capture_status='not_started',
                restoration_status='not_attempted',baseline_sha256=baseline['sha256'],stable_usb_identity_verified=True,
                usb_vid_pid='10c4:ea60',tool_sha256=sha(Path(__file__)),transmitted_event_count=None,
                SDR_decoding_proven=False,restore_policy='always after installation attempt')
    attempted=a.action=='restore';closed=True;cleaning=False;handlers={}
    def cancel(*_):
        if not cleaning:raise lifecycle_helpers.Cancelled('Native reference cancelled')
        print(json.dumps({'kind':'NATIVE_RESTORATION_IN_PROGRESS'}),flush=True)
    try:
        for sig in (signal.SIGINT,signal.SIGTERM):handlers[sig]=signal.signal(sig,cancel)
        if a.action=='run':
            lifecycle_helpers.current_baseline_check(a,baseline)
            attempted=True;install(a,data)
            record['artifact']=dict(manifest_sha256=sha(a.manifest),build_info_sha256=data['build_info_sha256'],
                parts=data['parts'],version=VERSION,source_commit=info['source_commit'],source_tree_sha256=info['source_tree_sha256'],idf_commit=SDK)
            record['capture_status']='in_progress';record['capture_attempted']=True
            result=collect(a);lifecycle_helpers.write_json(a.output/'capture.json',result)
            record['capture_status']=result['status']
            require(result['status']=='completed' and result['uart_closed'],'Native scan did not finish and close')
    except (Exception,KeyboardInterrupt) as error:
        record['error_kind']=type(error).__name__
        if record['capture_status']=='in_progress':record['capture_status']='failed'
        if isinstance(error,lifecycle_helpers.OwnedHardwareClosureError):closed=False
        lifecycle_helpers.write_json(a.private/'failure.json',{'error_kind':type(error).__name__,'error':str(error)})
        receipt=a.private/'scanner/capture.json'
        if receipt.exists():
            result=json.loads(receipt.read_text());lifecycle_helpers.write_json(a.output/'capture.json',result);record['capture_status']=result['status']
    finally:
        cleaning=True;record['owned_uart_worker_exit_confirmed']=closed
        if attempted and not closed:record['restoration_status']='blocked_owned_worker_not_closed'
        elif attempted:
            try:lifecycle_helpers.restore_verified(a,baseline);record['restoration_status']='verified'
            except Exception as error:
                record['restoration_status']='failed';record['restore_error_kind']=type(error).__name__
                if isinstance(error,lifecycle_helpers.OwnedHardwareClosureError):record['owned_uart_worker_exit_confirmed']=False
                lifecycle_helpers.write_json(a.private/'restore-failure.json',{'error_kind':type(error).__name__,'error':str(error)})
        if record['restoration_status']=='verified' and (a.action=='restore' or record['capture_status']=='completed') and 'error_kind' not in record:
            record['status']='completed'
        record['ended_utc']=lifecycle_helpers.utc();lifecycle_helpers.write_json(a.output/'native-reference.json',record)
        for sig,handler in handlers.items():signal.signal(sig,handler)
        os.umask(old_umask)
    print(json.dumps({'kind':'NATIVE_RUN_CLOSED','status':record['status'],'restoration_status':record['restoration_status']}),flush=True)
    return 0 if record['status']=='completed' else 2


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('run','restore','_capture'),nargs='?',default='run')
    p.add_argument('--artifact',type=Path);p.add_argument('--manifest',type=Path)
    p.add_argument('--port',default=lifecycle_helpers.STABLE_PORT,choices=[lifecycle_helpers.STABLE_PORT])
    p.add_argument('--private',type=Path,required=True);p.add_argument('--output',type=Path)
    a=p.parse_args(argv)
    if a.action=='_capture':
        os.umask(0o077);return capture(a)
    if a.output is None:p.error('run/restore requires fresh --output')
    if a.action=='run' and (a.artifact is None or a.manifest is None):p.error('run requires native --artifact and --manifest')
    (ROOT/'.scratch').mkdir(exist_ok=True)
    with (ROOT/'.scratch/esp-demo.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:p.error('Another ESP operator owns the lifecycle lock')
        return run(a)


if __name__=='__main__':raise SystemExit(main())
