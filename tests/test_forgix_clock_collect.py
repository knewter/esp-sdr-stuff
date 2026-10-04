"""One-shot retained clock transport tests with a real temporary flock."""
import errno,fcntl,json,os,pty,select,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import forgix_clock_collect as collect
import test_forgix_clock_profile as engine_tests

class Collector(unittest.TestCase):
 @classmethod
 def setUpClass(cls):engine_tests.Engine.setUpClass();cls.raw=engine_tests.Engine.run_c(engine_tests.Engine(),0)
 @classmethod
 def tearDownClass(cls):engine_tests.Engine.tearDownClass()
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.directory=Path(self.temp.name);self.lock=self.directory/'lock';self.fd=os.open(self.lock,os.O_RDWR|os.O_CREAT,0o600);fcntl.flock(self.fd,fcntl.LOCK_EX)
  self.n=0;self.closed=False;self.writes=0;self.data=self.raw;self.mode='normal'
 def tearDown(self):os.close(self.fd);self.temp.cleanup()
 def clock(self):self.n+=1;return self.n
 def admission(self):return {'clock_measurement_qualified':True,'lifecycle_admitted':True,'build_sha256':'22'*32,'image_sha256':'33'*32}
 def select(self):return {'identity':'synthetic fixture; no device'}
 def opened(self,identity,until):
  if self.mode=='late-open':self.n=30_000_000_000
  return self
 def write(self,raw,until):
  self.writes+=1
  if self.mode=='short':return 127
  if self.mode=='late-write':self.n=30_000_000_000
  return len(raw)
 def read(self,size,until):
  if self.mode=='prefix-error':
   e=OSError('fixture');e.consumed_prefix=self.data[:11];raise e
  chunk=self.data[:min(size,17)];self.data=self.data[len(chunk):]
  if self.mode=='late-read':self.n=34_000_000_000
  return chunk
 def close(self):
  self.closed=True
  if self.mode=='late-close':self.n=34_000_000_000
 def run_collect(self):
  return collect.collect(self.directory/'capture',b'\x11'*16,b'\x22'*32,b'\x33'*32,self.opened,self.admission,self.select,self.fd,self.lock,0,self.clock)
 def saved(self):return json.loads((self.directory/'capture/result.json').read_bytes())
 def test_real_flock_one_command_full_retained_replay(self):
  r=self.run_collect();self.assertEqual(r['status'],'digital_ratio_observed');self.assertEqual(self.writes,1);self.assertTrue(self.closed)
  self.assertEqual(collect.replay(self.directory/'capture',b'\x11'*16,b'\x22'*32,b'\x33'*32),r['validation'])
 def test_prefix_error_retains_every_consumed_byte_and_closes(self):
  self.mode='prefix-error'
  with self.assertRaises(OSError):self.run_collect()
  self.assertEqual((self.directory/'capture/raw.bin').read_bytes(),self.raw[:11]);self.assertTrue(self.closed);self.assertEqual(self.saved()['status'],'failed');self.assertEqual(self.writes,1)
 def test_each_late_transport_boundary_fails_without_retry(self):
  for mode in ('late-open','short','late-write','late-read','late-close'):
   with self.subTest(mode=mode):
    # Each run is independently fresh; transport accepts no fallback.
    self.mode=mode;self.data=self.raw;self.n=0;self.writes=0;self.closed=False
    target=self.directory/'capture'
    if target.exists():
     import shutil;shutil.rmtree(target)
    with self.assertRaises(Exception):self.run_collect()
    self.assertTrue(self.closed);self.assertLessEqual(self.writes,1);self.assertEqual(self.saved()['status'],'failed')
 def test_admission_or_lock_refusal_precedes_open_and_intent(self):
  with patch.object(self,'admission',return_value={}):
   with self.assertRaises(ValueError):self.run_collect()
  self.assertEqual(self.writes,0);self.assertFalse((self.directory/'capture').exists())
 def test_actual_final_result_fsync_fault_never_leaves_qualifying_receipt(self):
  actual=os.fsync
  def fault(fd):
   target=os.readlink('/proc/self/fd/'+str(fd))
   if target.endswith('/result.json'):raise OSError('fixture result fsync')
   return actual(fd)
  with patch.object(os,'fsync',side_effect=fault):
   with self.assertRaises(OSError):self.run_collect()
  self.assertEqual(self.saved()['status'],'failed');self.assertTrue((self.directory/'capture/finalization-pending.json').exists());self.assertTrue(self.closed)
 def test_actual_posix_bytewise_eio_preserves_consumed_prefix(self):
  from forgix_usb_ram_capture import open_retaining_serial
  from forgix_synthetic_backend import SyntheticTransport
  import serial.serialposix
  master,slave=pty.openpty();port=os.ttyname(slave);calls=[];actual=os.read;serial_handle=None
  try:
   with patch.object(serial.serialposix.Serial,'_update_dtr_state'),patch.object(serial.serialposix.Serial,'_update_rts_state'):
    serial_handle=open_retaining_serial(port)
   target=serial_handle.fileno();os.write(master,self.raw[:11]);self.assertTrue(select.select([target],[],[],1)[0])
   def fault(fd,size):
    if fd!=target:return actual(fd,size)
    calls.append(size)
    if len(calls)>11:raise OSError(errno.EIO,'actual target read fixture')
    return actual(fd,size)
   # Make the twelfth target syscall readable; the EIO is inside pyserial.
   os.write(master,b'!')
   transport=SyntheticTransport(serial_handle)
   boot=time.monotonic_ns()
   with patch.object(os,'read',side_effect=fault):
    with self.assertRaises(OSError):
     collect.collect(self.directory/'capture',b'\x11'*16,b'\x22'*32,b'\x33'*32,lambda i,d:transport,self.admission,self.select,self.fd,self.lock,boot)
   self.assertEqual(calls,[1]*12);self.assertEqual((self.directory/'capture/raw.bin').read_bytes(),self.raw[:11]);self.assertFalse(serial_handle.is_open);self.assertEqual(self.saved()['status'],'failed')
  finally:
   if serial_handle is not None:serial_handle.close()
   os.close(master);os.close(slave)
 def test_replay_refuses_public_or_unfinished_capture(self):
  self.run_collect();path=self.directory/'capture';os.chmod(path/'raw.bin',0o644)
  with self.assertRaisesRegex(ValueError,'private'):collect.replay(path,b'\x11'*16,b'\x22'*32,b'\x33'*32)
