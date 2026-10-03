#!/usr/bin/env python3
"""Offline codec/finite register-test plan. No serial opens, load or programmer."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import struct
import re
import time
import zlib

COUNTER=0x1000
SCRATCH=0x1004
ARM,READ,WRITE,FINISH=1,2,3,4
MAX_COMMANDS=24

def allowed(op,address,value):
 return ((op in (ARM,FINISH) and address==value==0) or
         (op==READ and address in (COUNTER,SCRATCH) and value==0) or
         (op==WRITE and address==SCRATCH))

def request(op,sequence,nonce,address=0,value=0):
 if not allowed(op,address,value) or not 1<=sequence<=MAX_COMMANDS or len(nonce)!=16 or not any(nonce):
  raise ValueError('register command outside the finite bridge contract')
 body=struct.pack('<4sBBHI16sII8s',b'FGSB',1,op,0,sequence,nonce,address,value,bytes(8))
 return body+struct.pack('<I',zlib.crc32(body))

def response(data,*,expected,source_hash):
 if len(data)!=128 or data[:5]!=b'FGSB\x01' or data[7] or zlib.crc32(data[:124])!=struct.unpack_from('<I',data,124)[0]:
  raise ValueError('damaged bridge response')
 if data[5]!=expected[5] or data[8:32]!=expected[8:32]:raise ValueError('response nonce/sequence/register mismatch')
 if data[44:108]!=source_hash.encode('ascii'):raise ValueError('wrong compiled bridge identity')
 if struct.unpack_from('<II',data,108)!=(32000000,150000000) or any(data[116:124]):
  raise ValueError('wrong declared clock profile/reserved fields')
 if data[6]!=0:raise ValueError('bridge refused or failed command: '+str(data[6]))
 return {'value':struct.unpack_from('<I',data,32)[0],'device_us':struct.unpack_from('<Q',data,36)[0]}

def plan(nonce):
 # First preserve scratch, then write/read patterns including a final zero bit.
 commands=[(ARM,0,0),(READ,SCRATCH,0),(READ,COUNTER,0)]
 for value in (0x1357ace0,0xa55a1122,0):commands.extend([(WRITE,SCRATCH,value),(READ,SCRATCH,0)])
 commands.append((READ,COUNTER,0))
 return [request(op,i+1,nonce,address,value) for i,(op,address,value) in enumerate(commands)]

def restore_and_finish(nonce,original,next_sequence):
 return [request(WRITE,next_sequence,nonce,SCRATCH,original),
         request(READ,next_sequence+1,nonce,SCRATCH),request(FINISH,next_sequence+2,nonce)]

class RegisterRun:
 """Finite host engine. Caller owns transport, USB identity, lock and recovery.

 Transport read(size, deadline)/write(data, deadline) must honor the absolute
 monotonic deadline. No port is opened here. Keep this object's raw transcript
 private, including failure prefixes. Ambiguous transport/framing poisons the
 session: never retry a possibly consumed command or guess its next sequence.
 """
 def __init__(self,transport,source_hash,nonce=None,clock=time.monotonic):
  if not isinstance(source_hash,str) or not re.fullmatch('[0-9a-f]{64}',source_hash):
   raise ValueError('expected compiled source-set SHA256 required')
  self.nonce=secrets.token_bytes(16) if nonce is None else nonce
  request(ARM,1,self.nonce)
  self.transport,self.source_hash,self.clock=transport,source_hash,clock
  self.deadline=clock()+30;self.next=1;self.previous_us=None;self.poisoned=False
  self.transcript=[];self.started=False;self.original=None
  self.restored=False;self.finished=False;self.patterns=[];self.counter_delta=None

 def within(self,until):
  if self.clock()>=until:raise TimeoutError('absolute register-test deadline expired')

 def exchange(self,op,address=0,value=0):
  if self.poisoned or self.finished:raise ValueError('session is closed or ambiguous')
  packet=request(op,self.next,self.nonce,address,value)
  entry={'request':packet,'sent':0,'response':bytearray(),'validated':False}
  self.transcript.append(entry);until=min(self.deadline,self.clock()+2)
  try:
   while entry['sent']<len(packet):
    self.within(until);chunk=packet[entry['sent']:]
    n=self.transport.write(chunk,until)
    if type(n) is not int or not 0<n<=len(chunk):raise ValueError('invalid transport write progress')
    entry['sent']+=n;self.within(until)
   while len(entry['response'])<128:
    self.within(until);left=128-len(entry['response'])
    chunk=self.transport.read(left,until)
    if not isinstance(chunk,bytes):raise ValueError('invalid transport read type')
    entry['response'].extend(chunk) # Retain even an invalid overlong prefix.
    if not 0<len(chunk)<=left:raise ValueError('empty or overlong transport read')
    self.within(until)
   reply=response(bytes(entry['response']),expected=packet,source_hash=self.source_hash)
   if self.previous_us is not None and reply['device_us']<self.previous_us:
    raise ValueError('device timestamp went backwards')
   self.within(until);self.previous_us=reply['device_us'];self.next+=1
   entry['validated']=True;return reply['value']
  except BaseException:
   self.poisoned=True;raise

 def run(self):
  if self.started:raise ValueError('one register test per session')
  self.started=True;error=None;cleanup_error=None
  try:
   if self.exchange(ARM)!=0:raise ValueError('unexpected ARM value')
   self.original=self.exchange(READ,SCRATCH)
   before=self.exchange(READ,COUNTER)
   for value in (0x1357ace0,0xa55a1122,0):
    if self.exchange(WRITE,SCRATCH,value)!=0:raise ValueError('unexpected write acknowledgment value')
    observed=self.exchange(READ,SCRATCH)
    self.patterns.append({'expected':value,'observed':observed})
    if observed!=value:raise ValueError('scratch pattern readback differs')
   after=self.exchange(READ,COUNTER);self.counter_delta=(after-before)&0xffffffff
   if not 0<self.counter_delta<0x80000000:raise ValueError('counter did not advance within an unambiguous wrap')
  except BaseException as exc:error=exc
  finally:
   # Only a fully validated transcript establishes the next safe command.
   if not self.poisoned:
    try:
     if self.original is not None:
      if self.exchange(WRITE,SCRATCH,self.original)!=0:raise ValueError('unexpected restore acknowledgment value')
      if self.exchange(READ,SCRATCH)!=self.original:raise ValueError('original scratch restoration differs')
      self.restored=True
    except BaseException as exc:cleanup_error=exc
    if not self.poisoned:
     try:
      if self.exchange(FINISH)!=0:raise ValueError('unexpected FINISH value')
      self.finished=True
     except BaseException as exc:
      if cleanup_error is None:cleanup_error=exc
  self.summary={'result':'passed' if error is None and cleanup_error is None and self.restored and self.finished else 'failed',
   'error_kind':None if error is None else type(error).__name__,
   'cleanup_error_kind':None if cleanup_error is None else type(cleanup_error).__name__,
   'scratch_restore_verified':self.restored,'finish_reply_verified':self.finished,
   'session_ambiguous':self.poisoned,'requests_attempted':len(self.transcript),
   'patterns':self.patterns,'counter_delta':self.counter_delta,
   'factory_return_verified':False,
   'scope':'Host register engine only. Caller must retain private raw transcript and independently verify full flash/factory return.'}
  for exc in (error,cleanup_error):
   if exc is not None and not isinstance(exc,Exception):raise exc
  return self.summary

def main():
 cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('--plan',required=True,type=Path);a=cli.parse_args()
 from build_forgix_usb_ram import fresh
 out=fresh(a.plan);nonce=secrets.token_bytes(16);commands=plan(nonce)
 (out/'requests.bin').write_bytes(b''.join(commands))
 receipt={'kind':'offline-register-plan','hardware_opened':False,'loading_admitted':False,
  'request_count':len(commands),'request_sha256':hashlib.sha256(b''.join(commands)).hexdigest(),
  'scope':'Save original scratch; verify three patterns and increasing counter; restore original scratch and verify before FINISH. No transport/reception claim.'}
 (out/'plan.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
