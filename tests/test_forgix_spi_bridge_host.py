"""Host engine against compiled device protocol plus injected transport faults.

The fake register bank is not physical FPGA/USB/PIO or recovery evidence.
"""
import ctypes as C
from pathlib import Path
import struct
import sys
import unittest
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import forgix_spi_bridge as host
import test_forgix_spi_bridge as native

class Device:
 def __init__(self,codec,*,fault=None):
  self.codec=codec;self.fault=fault;self.now=0.;self.pending=bytearray()
  self.replies=bytearray();self.session=native.Session();self.scratch=0xdeadbeef
  self.commands=[];self.us=1000;self.counters=iter((0xfffffff0,0x30))
 def write(self,data,deadline):
  self.now+=.001
  if self.fault=='write-zero':return 0
  if self.fault=='write-overlong':return len(data)+1
  n=min(7,len(data));self.pending.extend(data[:n])
  if len(self.pending)==48:
   packet=bytes(self.pending);self.pending.clear();r=native.Request()
   assert self.codec.bridge_parse((native.U8*48).from_buffer_copy(packet),C.byref(r))
   assert self.codec.bridge_admit(C.byref(self.session),C.byref(r),100000)==(1 if r.op==host.ARM else 2)
   self.commands.append((r.op,r.address,r.value));value=0
   if r.op==host.WRITE:self.scratch=r.value
   if r.op==host.READ:
    value=next(self.counters) if r.address==host.COUNTER else self.scratch
   if self.fault=='pattern' and r.sequence==5:value^=1
   if self.fault=='restore' and r.sequence==12:value^=1
   if self.fault=='counter-stuck' and r.sequence==10:value=0xfffffff0
   if self.fault=='counter-backward' and r.sequence==10:value=0xffffffef
   self.us+=100;out=(native.U8*128)()
   stamp=0 if self.fault=='timestamp' and r.sequence==5 else self.us
   self.codec.bridge_response(out,C.byref(r),0,value,stamp,b'a'*64)
   raw=bytearray(out)
   if r.sequence==5:
    if self.fault in ('crc','nonce','source','address','clock','status'):
     offset={'crc':127,'nonce':12,'source':44,'address':28,'clock':108,'status':6}[self.fault]
     raw[offset]^=1
     if self.fault!='crc':struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
   self.replies.extend(raw)
  return n
 def read(self,size,deadline):
  self.now+=.001
  if self.fault=='cancel':raise KeyboardInterrupt()
  if self.fault=='read-empty':return b''
  if self.fault=='read-overlong':return b'x'*(size+1)
  if self.fault=='late-ready':self.now=deadline
  n=min(9,size,len(self.replies));data=bytes(self.replies[:n]);del self.replies[:n]
  return data

class RegisterEngine(unittest.TestCase):
 @classmethod
 def setUpClass(cls):native.NativeProtocol.setUpClass()
 @classmethod
 def tearDownClass(cls):native.NativeProtocol.tearDownClass()
 def run_device(self,fault=None):
  device=Device(native.NativeProtocol.lib,fault=fault)
  engine=host.RegisterRun(device,'a'*64,b'x'*16,clock=lambda:device.now)
  return device,engine,engine.run()
 def test_fragmented_real_c_replies_verify_patterns_wrap_restore_and_finish(self):
  d,e,r=self.run_device();self.assertEqual(r['result'],'passed')
  self.assertEqual(r['counter_delta'],64);self.assertEqual(d.scratch,0xdeadbeef)
  self.assertTrue(r['scratch_restore_verified'] and r['finish_reply_verified'])
  self.assertFalse(r['factory_return_verified']);self.assertEqual(len(d.commands),13)
  self.assertEqual([x['observed'] for x in r['patterns']],[0x1357ace0,0xa55a1122,0])
  self.assertTrue(all(t['validated'] and t['sent']==48 and len(t['response'])==128 for t in e.transcript))
  with self.assertRaises(ValueError):e.run()
  with self.assertRaises(ValueError):e.exchange(host.READ,host.COUNTER)
 def test_valid_semantic_failure_restores_scratch_and_finishes(self):
  for fault in ('pattern','counter-stuck','counter-backward'):
   with self.subTest(fault=fault):
    d,e,r=self.run_device(fault);self.assertEqual(r['result'],'failed')
    self.assertTrue(r['scratch_restore_verified'] and r['finish_reply_verified'])
    self.assertFalse(r['session_ambiguous']);self.assertEqual(d.scratch,0xdeadbeef)
 def test_restore_readback_failure_finishes_but_never_reports_success(self):
  d,e,r=self.run_device('restore');self.assertEqual(r['result'],'failed')
  self.assertFalse(r['scratch_restore_verified']);self.assertTrue(r['finish_reply_verified'])
  self.assertEqual(r['cleanup_error_kind'],'ValueError')
 def test_ambiguous_replies_stop_without_retry_or_guessed_restore(self):
  for fault in ('crc','nonce','source','address','clock','status','timestamp'):
   with self.subTest(fault=fault):
    d,e,r=self.run_device(fault);self.assertEqual(r['result'],'failed')
    self.assertTrue(r['session_ambiguous']);self.assertEqual(len(d.commands),5)
    self.assertFalse(r['scratch_restore_verified'] or r['finish_reply_verified'])
    self.assertEqual(len(e.transcript[-1]['response']),128)
    with self.assertRaises(ValueError):e.exchange(host.FINISH)
 def test_transport_faults_retain_partial_prefix_and_never_resynchronize(self):
  for fault in ('write-zero','write-overlong','read-empty','read-overlong','late-ready'):
   with self.subTest(fault=fault):
    d,e,r=self.run_device(fault);self.assertEqual(r['result'],'failed')
    self.assertTrue(r['session_ambiguous']);self.assertEqual(len(e.transcript),1)
    self.assertLessEqual(len(d.commands),1)
    if fault=='read-overlong':self.assertEqual(len(e.transcript[0]['response']),129)
    if fault=='late-ready':self.assertEqual(len(e.transcript[0]['response']),9)
 def test_absolute_deadline_includes_transport_return_and_cleanup(self):
  d=Device(native.NativeProtocol.lib);e=host.RegisterRun(d,'a'*64,b'x'*16,clock=lambda:d.now)
  d.now=30;r=e.run();self.assertEqual(r['result'],'failed');self.assertFalse(d.commands)
  d=Device(native.NativeProtocol.lib);write=d.write
  def late_restore(data,deadline):
   n=write(data,deadline)
   if len(d.commands)==11:d.now=30
   return n
  d.write=late_restore;e=host.RegisterRun(d,'a'*64,b'x'*16,clock=lambda:d.now)
  r=e.run();self.assertEqual(r['result'],'failed');self.assertTrue(r['session_ambiguous'])
  self.assertFalse(r['scratch_restore_verified'] or r['finish_reply_verified'])
  self.assertEqual(d.scratch,0xdeadbeef) # Issued write alone is not verified restore.
  self.assertEqual(len(d.commands),11)
 def test_partial_write_and_partial_reply_exceptions_retain_prefixes(self):
  for side in ('write','read'):
   d=Device(native.NativeProtocol.lib);original=getattr(d,side);calls=[0]
   def interrupted(data,deadline):
    calls[0]+=1
    if calls[0]==3:raise TimeoutError('transport stall')
    return original(data,deadline)
   setattr(d,side,interrupted)
   e=host.RegisterRun(d,'a'*64,b'x'*16,clock=lambda:d.now);r=e.run()
   self.assertTrue(r['session_ambiguous']);self.assertEqual(r['result'],'failed')
   if side=='write':self.assertEqual(e.transcript[0]['sent'],14);self.assertFalse(d.commands)
   else:self.assertEqual(len(e.transcript[0]['response']),18);self.assertEqual(len(d.commands),1)
 def test_cancellation_propagates_with_failed_prefix_and_no_more_commands(self):
  d=Device(native.NativeProtocol.lib,fault='cancel')
  e=host.RegisterRun(d,'a'*64,b'x'*16,clock=lambda:d.now)
  with self.assertRaises(KeyboardInterrupt):e.run()
  self.assertTrue(e.poisoned);self.assertEqual(e.summary['result'],'failed')
  self.assertEqual(len(d.commands),1);self.assertEqual(len(e.transcript),1)
 def test_invalid_source_identity_is_rejected_before_transport(self):
  d=Device(native.NativeProtocol.lib)
  for source in ('a'*63,'A'*64,None):
   with self.assertRaises(ValueError):host.RegisterRun(d,source,b'x'*16)
  self.assertFalse(d.commands)

if __name__=='__main__':unittest.main()
