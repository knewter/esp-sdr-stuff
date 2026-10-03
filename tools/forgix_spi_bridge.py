#!/usr/bin/env python3
"""Offline codec/finite register-test plan. No serial opens, load or programmer."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import struct
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
