"""Backend faults use real protocol C and private files, never USB hardware."""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import forgix_spi_backend as backend
import forgix_spi_capture as capture
import forgix_usb_ram_trial as trial
import preserve_forgix as preserve
import test_forgix_config as config_tests
import test_forgix_spi_bridge as native
from test_forgix_spi_capture import Device

class Gates(unittest.TestCase):
    def profile(self):
        return {n:'a'*64 for n in ('elf_sha256','manifest_sha256','bridge_source_sha256',
                                 'bitstream_sha256','qualification_sha256','backend_source_sha256')}
    def test_registry_empty_and_booleans_cannot_admit(self):
        p=self.profile();p.update(qualification_verified=True,physical_execution_admitted=True)
        self.assertEqual(backend.QUALIFIED,())
        b=object.__new__(backend.Backend);b.used=False;b.profile=p
        b.inspector=SimpleNamespace(target=lambda *args:self.fail('device queried'))
        b.check_inputs=lambda:self.fail('inputs touched after refused registry')
        with self.assertRaisesRegex(ValueError,'No committed physical'):b.admit(30)
    def test_hidden_worker_refuses_before_artifact_or_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'request.json';p.write_text(json.dumps({'profile':self.profile()}))
            with patch.object(trial,'private_file',return_value=p), patch.object(backend,'artifact',side_effect=AssertionError('artifact')):
                with self.assertRaisesRegex(ValueError,'No committed physical'):backend.serial_worker(p)
    def test_unknown_worker_or_container_closure_blocks_all_access(self):
        w=SimpleNamespace(closed=True);o=backend.AggregateOwner(w)
        r=SimpleNamespace(hardware_process_closed=True);o.runners.append(r)
        self.assertTrue(o.closed)
        for who in ('worker','container','unknown'):
            w.closed=who!='worker';r.hardware_process_closed=who!='container';o.unknown=who=='unknown'
            self.assertFalse(o.closed)
            b=object.__new__(backend.Backend);b.owner=o
            with patch.object(backend,'inherited_operator_lock',side_effect=AssertionError('lock/device reached')):
                with self.assertRaisesRegex(ValueError,'Unknown owned'):b.check_inputs()
    def test_exact_rom_ram_args_and_original_usb_whitelist(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'ram-spi-bridge.elf';p.write_bytes(b'synthetic fixture')
            r=object.__new__(backend.RegisterPicotool);r.bridge={'elf_sha256':trial.sha(p)}
            t=SimpleNamespace(pid=preserve.BOOT_PID,bus=3,address=9)
            with patch.object(backend,'inspect_elf',return_value={}) as guard:
                self.assertEqual(r.load_args(t,p,Path('/private')/p.name),
                                 ['load','-v','-x','/private/ram-spi-bridge.elf','-t','elf','--bus','3','--address','9'])
                self.assertEqual(guard.call_args.kwargs,{'application':'spi-config-bridge'})
                for pid,name,digest in ((preserve.FACTORY_PID,p.name,trial.sha(p)),
                                        (preserve.BOOT_PID,'ram-diagnostic.elf',trial.sha(p)),
                                        (preserve.BOOT_PID,p.name,'0'*64)):
                    t.pid=pid;r.bridge['elf_sha256']=digest
                    with self.assertRaises(ValueError):r.load_args(t,p,Path('/private')/name)
            legacy=object.__new__(trial.OwnedPicotool)
            with self.assertRaisesRegex(preserve.PreservationError,'RAM image changed'):legacy.load_args(t,p,Path('/private/ram-diagnostic.elf'))
    def test_preservation_translation_requires_two_full_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=object.__new__(backend.Backend);b.private=Path(tmp)/'session';b.private.mkdir()
            b.inspector=SimpleNamespace(deadline=None);b.environment={'picotool_executable':'fixture','image_id':'fixture'}
            b.frozen={};b.lockfd=1;b.profile={'uid_sha256':'b'*64,'baseline_sha256':'a'*64}
            b.owner=backend.AggregateOwner(SimpleNamespace(closed=True))
            b.hardware_gate=lambda until:None
            r={'backups':{'sha256':'a'*64,'bytes_per_read':2097152,'reads':2,'matching':True},
               'independent_device_verify':True,'status':'preserved_and_returned'}
            with patch.object(backend,'ROOT',Path(tmp)):
                (Path(tmp)/'backups').mkdir()
                b.private=Path(tmp)/'backups/session';b.private.mkdir()
                with patch.object(trial,'full_preservation',return_value=(r,SimpleNamespace(hardware_process_closed=True))):
                    out=b.preservation('before',30)
                    self.assertEqual(out['flash_bytes'],2097152);self.assertEqual(out['read_sha256'],['a'*64]*2)
                    r['backups']['reads']=1
                    with self.assertRaisesRegex(ValueError,'Fresh original'):b.preservation('after',30)
    def test_changed_configuration_source_refuses_transition_before_device(self):
        b=object.__new__(backend.Backend)
        b.hardware_gate=lambda until:None
        b.profile={'bitstream_sha256':'a'*64,'bridge_source_sha256':'b'*64}
        b.configuration={'bitstream_sha256':'a'*64,'source_sha256':'c'*64}
        with patch.object(trial,'fresh_tty',side_effect=AssertionError('device')):
            with self.assertRaisesRegex(ValueError,'selected image/source'):b.transition(30)
    def test_direct_hardware_methods_require_admitted_session(self):
        b=object.__new__(backend.Backend);b.admitted=False
        for operation in ('preserve_before','preserve_after','enter_rom','load_ram','configure','collect','transition','return_factory'):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(ValueError,'session has not been admitted'):getattr(b,operation)(30)
    def test_changed_preservation_and_backend_inputs_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.scratch').mkdir();(root/'tools').mkdir()
            paths={name:root/name for name in ('tool','python','elf','binding','qualification','tools/forgix_spi_backend.py')}
            for p in paths.values():p.write_bytes(b'fixture')
            b=object.__new__(backend.Backend);b.owner=backend.AggregateOwner(SimpleNamespace(closed=True))
            b.lockfd=1;b.lockpath=root/'.scratch/lock';b.frozen={'inputs':dict.fromkeys(('tools/forgix_spi_backend.py','tools/forgix_spi_qualifications.py'),'fixture')}
            b.environment={name:str(paths[p]) for name,p in [('picotool_executable','tool'),('python_executable','python')]}
            b.environment.update({name+'_sha256':trial.sha(Path(b.environment[name])) for name in ('picotool_executable','python_executable')})
            binding={'binding_path':str(paths['binding']),'binding_sha256':trial.sha(paths['binding']),
                     'baseline_paths':['fixture-a','fixture-b'],'baseline_sha256':'b'*64,'uid_sha256':'c'*64}
            b.profile=dict(binding,elf=str(paths['elf']),elf_sha256=trial.sha(paths['elf']),
                           backend_source_sha256=trial.sha(paths['tools/forgix_spi_backend.py']),
                           qualification_path=str(paths['qualification']),qualification_sha256=trial.sha(paths['qualification']))
            with patch.object(backend,'ROOT',root), patch.object(backend,'inherited_operator_lock',return_value={}), \
                 patch.object(trial,'check_inputs'),patch.object(trial,'original_binding',return_value=binding), \
                 patch.object(trial,'private_file',return_value=paths['qualification']):
                b.check_inputs()
                for name in ('tool','python','elf','tools/forgix_spi_backend.py','qualification'):
                    paths[name].write_bytes(b'changed')
                    with self.assertRaises((ValueError,preserve.PreservationError)):b.check_inputs()
                    paths[name].write_bytes(b'fixture')
                with patch.object(trial,'original_binding',return_value=dict(binding,uid_sha256='d'*64)):
                    with self.assertRaisesRegex(ValueError,'preservation binding'):b.check_inputs()

class Identity(unittest.TestCase):
    def test_uid_normalized_missing_wrong_and_reenumerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);usb=root/'bus/usb/devices/3-3';usb.mkdir(parents=True)
            for name,value in {'idVendor':'cafe','idProduct':'4012','product':'Forgix SPI RAM bridge v1',
                               'busnum':'3','devnum':'9','serial':'A1B2C3D4E5F60708'}.items():
                (usb/name).write_text(value)
            interface=usb/'3-3:1.0';interface.mkdir()
            tty=root/'class/tty/ttyACM9';tty.mkdir(parents=True);(tty/'device').symlink_to(interface)
            port=root/'ttyACM9';port.touch();uid=hashlib.sha256(b'a1b2c3d4e5f60708').hexdigest()
            first=capture.select_bridge('3-3',port,root,False,uid)
            self.assertEqual(first['uid_sha256'],uid)
            (usb/'devnum').write_text('10')
            self.assertNotEqual(first,capture.select_bridge('3-3',port,root,False,uid))
            for value in ('0000000000000000','bad',''):
                (usb/'serial').write_text(value)
                with self.assertRaises(ValueError):capture.select_bridge('3-3',port,root,False,uid)
            (usb/'serial').unlink()
            with self.assertRaises(FileNotFoundError):capture.select_bridge('3-3',port,root,False,uid)

class ConfigDevice:
    def __init__(self,codec):self.codec=codec;self.sent=bytearray();self.raw=None;self.close_calls=0
    def write(self,data,until):
        n=min(len(data),7);self.sent.extend(data[:n])
        if len(self.sent)==48:
            nonce=int.from_bytes(self.sent[8:12],'little');out=(C.c_uint8*128)()
            self.codec.bridge_config_reply(out,nonce,0,4321,config_tests.SOURCE.encode());self.raw=bytes(out)
        return n
    def read(self,n,until):
        part=self.raw[:min(n,11)];self.raw=self.raw[len(part):];return part
    def close(self):self.close_calls+=1

class Serial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):config_tests.Native.setUpClass();native.NativeProtocol.setUpClass()
    @classmethod
    def tearDownClass(cls):native.NativeProtocol.tearDownClass();config_tests.Native.tearDownClass()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);self.store=capture.PrivateCapture(root/'run',root)
        self.identity={'port':'synthetic-only','enumeration':'fixture'}
        self.request={'action':'configure','profile':{'bitstream_sha256':config_tests.HASH,'bridge_source_sha256':config_tests.SOURCE},
                      'until':30,'lockfd':1,'lockpath':'fixture'}
        self.device=ConfigDevice(config_tests.Native.lib);self.select=lambda:dict(self.identity);self.opens=0;self.now=0
    def run_serial(self):
        def opened(*args):self.opens+=1;return self.device
        with patch.object(backend,'inherited_operator_lock',return_value={'fixture':True}):
            return backend.serial_operation(self.request,self.store,self.select,opened,lambda:self.now)
    def test_actual_c_configuration_reply_persisted_and_closed(self):
        out=self.run_serial();self.assertEqual(out['status'],'configuration_indicated')
        self.assertTrue(out['persistence_verified'] and out['transport_closed']);self.assertFalse(out['physical_configuration_verified'])
        self.assertEqual(out['source_sha256'],config_tests.SOURCE);self.assertEqual(self.device.close_calls,1)
        retained=json.loads((self.store.path/'retained-prefix.json').read_text());self.assertEqual(len(bytes.fromhex(retained['response_hex'])),128)
    def test_prefix_disk_failure_still_closes_without_retry(self):
        durable=capture.durable
        def fail(stream,data):
            if b'"phase": "prefix"' in data and Path(os.readlink('/proc/self/fd/'+str(stream.fileno()))).name=='journal.jsonl':raise OSError('fixture disk full')
            return durable(stream,data)
        with patch.object(capture,'durable',fail):
            with self.assertRaises(OSError):self.run_serial()
        self.assertEqual(self.device.close_calls,1);self.assertEqual(len(self.device.sent),48)
        retained=json.loads((self.store.path/'retained-prefix.json').read_text());self.assertEqual(len(bytes.fromhex(retained['response_hex'])),11)
    def test_prefix_save_failure_cannot_skip_close(self):
        with patch.object(capture,'save',side_effect=OSError('fixture disk full')):
            with self.assertRaises(OSError):self.run_serial()
        self.assertEqual(self.device.close_calls,1)
    def test_identity_changes_after_open_closes_before_io(self):
        calls=[0]
        def changed():
            calls[0]+=1;return self.identity if calls[0]<3 else {'port':'synthetic-only','enumeration':'changed'}
        self.select=changed
        with self.assertRaises(ValueError):self.run_serial()
        self.assertEqual(self.device.close_calls,1);self.assertFalse(self.device.sent)
    def test_expected_config_identity_refuses_collection_before_open(self):
        self.request.update(action='collect',expected_identity={'port':'other'})
        with self.assertRaisesRegex(ValueError,'Prior configuration'):self.run_serial()
        self.assertEqual(self.opens,0)
    def test_actual_c_collection_closes_once_and_preserves_scratch(self):
        self.request.update(action='collect',expected_identity=self.identity);self.device=Device(native.NativeProtocol.lib)
        out=self.run_serial();self.assertEqual(out['status'],'registers_verified');self.assertEqual(self.device.close_calls,1)
        self.assertEqual(out['raw_bytes'],1664);self.assertEqual(self.device.scratch,0xdeadbeef)
        self.assertFalse(out['physical_qualification_proved'])
    def test_failed_collect_closes_and_retains_prefix(self):
        self.request['action']='collect';self.device=Device(native.NativeProtocol.lib,fault='crc')
        with self.assertRaisesRegex(ValueError,'Register collection failed'):self.run_serial()
        self.assertEqual(self.device.close_calls,1);self.assertEqual((self.store.path/'raw.bin').stat().st_size,640)
    def test_close_or_late_cleanup_cannot_pass(self):
        def late():self.device.close_calls+=1;self.now=30
        self.device.close=late
        with self.assertRaises(ValueError):self.run_serial()
        self.assertEqual(self.device.close_calls,1)
    def test_close_failure_cannot_return_success(self):
        def failed():self.device.close_calls+=1;raise OSError('fixture close failure')
        self.device.close=failed
        with self.assertRaises(OSError):self.run_serial()
        self.assertEqual(self.device.close_calls,1)
    def test_cancellation_after_partial_read_keeps_prefix_and_closes(self):
        read=self.device.read;calls=[0]
        def cancelled(n,until):
            calls[0]+=1
            if calls[0]==2:raise KeyboardInterrupt()
            return read(n,until)
        self.device.read=cancelled
        with self.assertRaises(KeyboardInterrupt):self.run_serial()
        self.assertEqual(self.device.close_calls,1);self.assertEqual(len(self.device.sent),48)
        self.assertEqual(len(bytes.fromhex(json.loads((self.store.path/'retained-prefix.json').read_text())['response_hex'])),11)

class Descriptor(unittest.TestCase):
    def test_actual_descriptor_c_advertises_uid_in_utf16(self):
        compiler=shutil.which('cc')
        self.assertTrue(compiler and str(Path(compiler).resolve()).startswith('/nix/store/'))
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);(d/'pico').mkdir()
            (d/'pico/unique_id.h').write_text('#include <stddef.h>\n#define PICO_UNIQUE_BOARD_ID_SIZE_BYTES 8\nvoid pico_get_unique_board_id_string(char*,size_t);\n')
            (d/'tusb.h').write_text('''#include <stdint.h>
typedef struct { uint8_t bLength,bDescriptorType; uint16_t bcdUSB; uint8_t bDeviceClass,bDeviceSubClass,bDeviceProtocol,bMaxPacketSize0; uint16_t idVendor,idProduct,bcdDevice; uint8_t iManufacturer,iProduct,iSerialNumber,bNumConfigurations; } tusb_desc_device_t;
#define TUSB_DESC_DEVICE 1
#define TUSB_CLASS_MISC 239
#define MISC_SUBCLASS_COMMON 2
#define MISC_PROTOCOL_IAD 1
#define TUSB_DESC_STRING 3
#define TUD_CONFIG_DESC_LEN 9
#define TUD_CDC_DESC_LEN 66
#define TUD_CONFIG_DESCRIPTOR(...) 0
#define TUD_CDC_DESCRIPTOR(...) 0
''')
            (d/'adapter.c').write_text('''#include "tusb.h"
#include <stddef.h>
#include <string.h>
void pico_get_unique_board_id_string(char *p,size_t n){if(n>=17)memcpy(p,"A1B2C3D4E5F60708",17);}
const uint8_t *tud_descriptor_device_cb(void);
unsigned serial_index(void){return ((const tusb_desc_device_t*)tud_descriptor_device_cb())->iSerialNumber;}
''')
            subprocess.run([compiler,'-Wall','-Wextra','-Werror','-shared','-fPIC','-I'+str(d),
                            str(ROOT/'firmware/forgix-spi-bridge/usb_descriptors.c'),str(d/'adapter.c'),'-o',str(d/'usb.so')],
                           check=True,capture_output=True,timeout=30)
            lib=C.CDLL(str(d/'usb.so'));lib.tud_descriptor_string_cb.argtypes=[C.c_uint8,C.c_uint16]
            lib.tud_descriptor_string_cb.restype=C.POINTER(C.c_uint16)
            self.assertEqual(lib.serial_index(),3)
            uid=lib.tud_descriptor_string_cb(3,0x409);self.assertEqual(uid[0],0x322)
            self.assertEqual(''.join(chr(uid[i]) for i in range(1,17)),'A1B2C3D4E5F60708')
            self.assertEqual(lib.tud_descriptor_string_cb(0,0)[1],0x409)
            self.assertFalse(lib.tud_descriptor_string_cb(4,0))
