"""Native observer metadata and preservation lifecycle; all hardware is mocked."""
import copy
import io
import json
from pathlib import Path
import signal
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import hashlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import native_ble_reference as native
import build_native_ble_reference as build

NONCE='0123456789abcdef'
SECOND=1000000000


def ready():return dict(schema=1,kind='READY',version=build.VERSION,nonce=NONCE,scan_start_us=1000000,scan_status=0)


def bucket(kind='AGG',sequence=1,start=1000000,end=2000000,count=2,total=2):
    r=dict(schema=1,kind=kind,version=build.VERSION,nonce=NONCE,sequence=sequence,interval_start_us=start,
           interval_end_us=end,owned_interval=count,owned_total=total,rssi_known=count,
           rssi_sum=-50*count,rssi_min=-50 if count else None,rssi_max=-50 if count else None)
    if kind=='END':r.update(scan_status=0,elapsed_us=end-1000000,scan_ms=90000)
    return r


def configured():
    r=native.Records(NONCE);r.accept(copy.deepcopy(native.CONFIG),0,1);r.accept(ready(),SECOND,SECOND+1000);return r


class NativeRecordsTests(unittest.TestCase):
    def test_full_scan_requires_ready_then_consecutive_exact_cumulative_end(self):
        r=configured();r.accept(bucket(),2*SECOND,2*SECOND+1000)
        r.accept(bucket('END',2,2000000,91000000,3,5),91*SECOND,91*SECOND+1000)
        self.assertEqual(r.total,5);self.assertEqual(r.end['elapsed_us'],90000000)
        self.assertEqual(r.rows[0]['host_line_start_ns'],2*SECOND)
        self.assertEqual(r.rows[1]['interval_start_us'],r.rows[0]['interval_end_us'])

    def test_config_field_types_and_extra_foreign_fields_rejected(self):
        for field,value in [('passive',1),('filter_duplicates',0),('uart_baud',921600),('schema',1.0),('address','foreign')]:
            with self.subTest(field=field),self.assertRaises(native.ProtocolError):
                native.Records(NONCE).accept({**native.CONFIG,field:value},0,1)

    def test_nonce_readiness_and_restarts_rejected(self):
        for nonce in ('',NONCE+'0','g'*16,'Ａ'*16):
            with self.assertRaises(native.ProtocolError):native.Records(nonce)
        for record in ({**ready(),'nonce':'a'*16},{**ready(),'scan_status':1},{**ready(),'scan_status':False}):
            r=native.Records(NONCE);r.accept(native.CONFIG,0,1)
            with self.assertRaises(native.ProtocolError):r.accept(record,2,3)
        for record in (native.CONFIG,ready()):
            with self.assertRaises(native.ProtocolError):configured().accept(record,2*SECOND,2*SECOND+1)

    def test_gap_counter_timing_and_rssi_fail_instead_of_publishing(self):
        for field,value in [('sequence',2),('owned_total',3),('interval_start_us',1000001),
                            ('interval_end_us',900000),('owned_interval',True),('rssi_known',3),
                            ('rssi_sum',-500),('rssi_min',-128),('foreign_payload','unsafe')]:
            with self.subTest(field=field),self.assertRaises(native.ProtocolError):
                configured().accept({**bucket(),field:value},2*SECOND,2*SECOND+1)

    def test_terminal_status_duration_and_full_host_observation_required(self):
        good=bucket('END',1,1000000,91000000)
        for field,value in [('scan_status',1),('elapsed_us',1000000),('scan_ms',90000.0),('sequence',0)]:
            with self.subTest(field=field),self.assertRaises(native.ProtocolError):
                configured().accept({**good,field:value},91*SECOND,91*SECOND+1)
        with self.assertRaises(native.ProtocolError):configured().accept(good,2*SECOND,2*SECOND+1)

    def test_init_error_and_zero_owned_result_are_explicit(self):
        with self.assertRaisesRegex(native.ProtocolError,'initialization/runtime'):
            native.Records(NONCE).accept(dict(schema=1,kind='ERROR',version=build.VERSION,stage='NVS',code=4353),0,1)
        r=configured();r.accept(bucket('END',end=91000000,count=0,total=0),91*SECOND,91*SECOND+1)
        self.assertEqual(r.total,0);self.assertIsNone(r.end['rssi_min'])


class NativePreflightTests(unittest.TestCase):
    def test_generated_observer_roles_and_logging_are_checked(self):
        config='\n'.join(build.REQUIRED)+'\n';build.validate_config(config)
        for required in ('CONFIG_BT_NIMBLE_ROLE_OBSERVER=y','# CONFIG_BT_NIMBLE_ROLE_CENTRAL is not set',
                         'CONFIG_BT_NIMBLE_LOG_LEVEL_NONE=y','CONFIG_LOG_DEFAULT_LEVEL_NONE=y'):
            with self.assertRaises(ValueError):build.validate_config(config.replace(required,'UNSAFE=y'))

    def test_partition_layout_checksum_and_extra_partition_fail(self):
        entries=b''
        for kind,subtype,offset,size,label in ((1,2,0x9000,0x6000,b'nvs'),(1,1,0xf000,0x1000,b'phy_init'),(0,0,0x10000,0x100000,b'factory')):
            entries+=struct.pack('<HBBII16sI',0x50aa,kind,subtype,offset,size,label,0)
        table=entries+b'\xeb\xeb'+b'\xff'*14+hashlib.md5(entries).digest()+b'\xff'*(3072-128)
        native.partition_check(table)
        for where in (8,112,128):
            corrupted=bytearray(table);corrupted[where]^=1
            with self.assertRaises(native.ProtocolError):native.partition_check(bytes(corrupted))

    def test_existing_SDR_manifest_cannot_enter_native_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'.scratch/artifact';folder.mkdir(mode=0o700,parents=True)
            for name,value in [('manifest.json',dict(schema=1,kind='receiver',target='esp32',version=build.VERSION)),('build-info.json',dict(kind='receiver'))]:
                (folder/name).write_text(json.dumps(value));(folder/name).chmod(0o600)
            (folder/'sdkconfig').write_text('');(folder/'sdkconfig').chmod(0o600)
            with patch.object(native,'ROOT',root),self.assertRaisesRegex(native.ProtocolError,'Explicit native profile'):
                native.validate_artifact(folder,folder/'manifest.json')


class NativeCaptureFailureTests(unittest.TestCase):
    def test_received_budget_overflow_retains_exact_saved_prefix_after_UART_close(self):
        class UART:
            def __init__(self):self.chunks=iter((b'boot\n',b'x'*2000001));self.closed=False
            def read(self,_):return next(self.chunks)
            def close(self):self.closed=True
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=SimpleNamespace(port='mock',private=root/'.scratch/scanner');uart=UART()
            with patch.object(native,'ROOT',root),patch.object(native.subprocess,'run',return_value=SimpleNamespace(returncode=0)),\
                 patch.object(native.lifecycle_helpers,'identity_check'),patch.object(native.lifecycle_helpers,'open_board',return_value=uart):
                self.assertEqual(native.capture(a),2)
            record=json.loads((a.private/'capture.json').read_text())
            self.assertTrue(uart.closed);self.assertEqual(record['received_uart_bytes'],2000006)
            self.assertEqual(record['saved_uart_bytes_private'],5)
            self.assertEqual(record['saved_uart_sha256'],hashlib.sha256(b'boot\n').hexdigest())
            self.assertFalse(record['all_received_uart_bytes_saved']);self.assertTrue(record['saved_uart_file_verified'])

    def test_writer_failure_emits_failed_fence_and_never_claims_missing_log_hash(self):
        class UART:
            closed=False
            def read(self,_):return b'boot\n'
            def close(self):self.closed=True
        class Writer:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def write(self,_):raise OSError('synthetic storage failure')
        original=Path.open
        def opened(path,*args,**kwargs):
            if path.name=='uart.bin':return Writer()
            return original(path,*args,**kwargs)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=SimpleNamespace(port='mock',private=root/'.scratch/scanner');uart=UART()
            with patch.object(native,'ROOT',root),patch.object(native.subprocess,'run',return_value=SimpleNamespace(returncode=0)),\
                 patch.object(native.lifecycle_helpers,'identity_check'),patch.object(native.lifecycle_helpers,'open_board',return_value=uart),patch.object(Path,'open',opened):
                self.assertEqual(native.capture(a),2)
            record=json.loads((a.private/'capture.json').read_text())
            self.assertTrue(uart.closed);self.assertEqual(record['status'],'failed')
            self.assertFalse(record['saved_uart_file_verified']);self.assertIsNone(record['saved_uart_sha256'])

    def test_internal_capture_cannot_store_UART_in_public_evidence_or_open_device(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=SimpleNamespace(port='mock',private=root/'docs/evidence/unsafe')
            with patch.object(native,'ROOT',root),patch.object(native.lifecycle_helpers,'identity_check') as identity,\
                 patch.object(native.lifecycle_helpers,'open_board') as opened,self.assertRaises(native.ProtocolError):
                native.capture(a)
            identity.assert_not_called();opened.assert_not_called();self.assertFalse(a.private.exists())


class NativeLifecycleTests(unittest.TestCase):
    def exercise(self,operation='success',capture_error=None,install_error=None,current_error=None,restore_callback=None):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=SimpleNamespace(action=operation if operation=='restore' else 'run',
                artifact=root/'artifact',manifest=root/'manifest',output=root/'public',private=root/'private',port='mock')
            data=dict(parts=[],build_info_sha256='b'*64);info=dict(source_commit='c'*40,source_tree_sha256='d'*64)
            h=native.lifecycle_helpers
            with patch.object(h,'baseline_check',return_value={'sha256':'a'*64}),patch.object(native,'security_check'),\
                 patch.object(h,'identity_check'),patch.object(native,'validate_artifact',return_value=(data,info)),\
                 patch.object(h,'validate_paths',return_value=(a.output,a.private)),\
                 patch.object(h,'current_baseline_check',side_effect=current_error) as before,\
                 patch.object(native,'install',side_effect=install_error) as install,\
                 patch.object(native,'sha',return_value='f'*64),\
                 patch.object(native,'collect',side_effect=capture_error,return_value={'status':'completed','uart_closed':True}) as collect,\
                 patch.object(h,'restore_verified',side_effect=restore_callback) as restore,patch('sys.stdout',new=io.StringIO()):
                result=native.run(a);receipt=json.loads((a.output/'native-reference.json').read_text())
                return result,receipt,install.call_count,collect.call_count,restore.call_count,before.call_count

    def test_success_restores_and_direct_restore_does_not_require_current_baseline(self):
        code,r,installed,captured,restored,before=self.exercise()
        self.assertEqual((code,installed,captured,restored,before),(0,1,1,1,1));self.assertEqual(r['restoration_status'],'verified')
        self.assertEqual(self.exercise('restore')[2:],(0,0,1,0))

    def test_unknown_current_image_refuses_install_without_mutating(self):
        code,r,installed,captured,restored,before=self.exercise(current_error=RuntimeError('unknown image'))
        self.assertEqual((code,installed,captured,restored,before),(2,0,0,0,1))

    def test_any_install_attempt_or_capture_cancel_restores(self):
        for install_error,capture_error in [(RuntimeError('write failure'),None),(None,RuntimeError('capture failure')),
                (None,native.lifecycle_helpers.Cancelled('cancel'))]:
            with self.subTest(install_error=install_error,capture_error=capture_error):
                code,r,*counts=self.exercise(install_error=install_error,capture_error=capture_error)
                self.assertEqual(code,2);self.assertEqual(counts[2],1);self.assertEqual(r['restoration_status'],'verified')
                if capture_error:self.assertEqual(r['capture_status'],'failed');self.assertTrue(r['capture_attempted'])

    def test_unconfirmed_UART_group_closure_blocks_restore(self):
        error=native.lifecycle_helpers.OwnedHardwareClosureError('unclosed descendant')
        for kwargs in ({'install_error':error},{'capture_error':error}):
            code,r,*counts=self.exercise(**kwargs)
            self.assertEqual(code,2);self.assertEqual(counts[2],0)
            self.assertEqual(r['restoration_status'],'blocked_owned_worker_not_closed')

    def test_cancel_during_restore_is_deferred_by_cleaning_handler(self):
        def restoration(*_):signal.getsignal(signal.SIGINT)(signal.SIGINT,None)
        code,r,*counts=self.exercise(capture_error=native.lifecycle_helpers.Cancelled('cancel'),restore_callback=restoration)
        self.assertEqual(counts[2],1);self.assertEqual(r['restoration_status'],'verified')
