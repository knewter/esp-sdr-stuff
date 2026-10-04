"""Offline exact-image preparation and injected configuration handshake; no device CLI."""
import hashlib
import json
from pathlib import Path
import re
import struct
import time
import zlib

def candidate(folder):
    from build_forgix_usb_ram import ROOT
    folder=Path(folder).absolute()
    if not folder.is_relative_to(ROOT/'.scratch') or '..' in folder.parts:
        raise ValueError('Private candidate directory required')
    for p in (folder,*folder.parents):
        if p.is_symlink():raise ValueError('Symlinked candidate input')
        if p==ROOT:break
    manifest=folder/'result.json'
    image=folder/'work/gateware/outflow/forgix_candidate.hex'
    for p,bound in ((manifest,128*1024),(image,1024*1024)):
        for a in (p,*p.parents):
            if a.is_symlink():raise ValueError('Symlinked candidate input')
            if a==folder:break
        if not p.is_file() or p.stat().st_nlink!=1 or not 0<p.stat().st_size<=bound:
            raise ValueError('Missing or oversized candidate input')
    mbytes=manifest.read_bytes();m=json.loads(mbytes);raw=image.read_bytes()
    if (m.get('status')!='passed' or m.get('device')!='T8F49' or m.get('timing_model')!='I2'
        or m.get('configuration_mode')!='passive' or m.get('stages')!=['map','interface','pnr','pgm']
        or m.get('owned_process_group_closed') is not True
        or m.get('private_generated_files_verified') is not True
        or not isinstance(m.get('source_commit'),str) or not re.fullmatch('[0-9a-f]{40}',m['source_commit'])
        or m.get('bitstream_bytes')!=len(raw) or m.get('bitstream_sha256')!=hashlib.sha256(raw).hexdigest()):
        raise ValueError('Successful exact provisional candidate required')
    # The pinned factory host decodes all hex bytes, including the prefix.
    # Keep this intentionally narrower than its generic Intel HEX/binary parser.
    if not re.fullmatch(rb'(?:[0-9a-fA-F]{2}\n)+',raw):
        raise ValueError('Reviewed one-byte-per-line Efinity hex required')
    data=bytes.fromhex(raw.decode())
    if not 0<len(data)<=196608:raise ValueError('Embedded image exceeds 192 KiB bound')
    return data,{'candidate_source_commit':m['source_commit'],
                 'candidate_manifest_sha256':hashlib.sha256(mbytes).hexdigest(),
                 'hex_sha256':hashlib.sha256(raw).hexdigest(),
                 'decoded_sha256':hashlib.sha256(data).hexdigest(),
                 'decoded_bytes':len(data),'decoded_crc32':zlib.crc32(data),
                 'physical_qualification_proved':False}

def digest(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):
        raise ValueError('Exact SHA256 required')
    return bytes.fromhex(value)

def request(image_hash,nonce):
    if type(nonce) is not int or not 0<nonce<=0xffffffff:raise ValueError('Nonzero uint32 nonce required')
    body=struct.pack('<4sBBHI32s',b'FGSC',1,1,0,nonce,digest(image_hash))
    return body+struct.pack('<I',zlib.crc32(body))

def response(raw,*,image_hash,source_hash,nonce):
    digest(source_hash)
    if (len(raw)!=128 or raw[:5]!=b'FGSC\x01' or any(raw[6:8]) or any(raw[116:124])
        or struct.unpack_from('<I',raw,8)[0]!=nonce or raw[20:52]!=digest(image_hash)
        or raw[52:116]!=source_hash.encode()
        or struct.unpack_from('<I',raw,124)[0]!=zlib.crc32(raw[:124])):
        raise ValueError('Configuration reply identity/framing differs')
    if raw[5]:raise ValueError('Configuration refused or failed: '+str(raw[5]))
    return {'device_us':struct.unpack_from('<Q',raw,12)[0],
            'bitstream_sha256':image_hash,'configuration_indication':True,
            'physical_configuration_verified':False}

def exchange(transport,*,image_hash,source_hash,nonce,until,write_event,clock=time.monotonic):
    """Caller owns identity/lock/closure/recovery. Persist prefixes; never retry.

    Receipt binds the firmware's indication, not measured image continuity.
    Transport read/write and durable sink must honor the caller's deadline.
    """
    packet=request(image_hash,nonce);digest(source_hash)
    def within():
        if clock()>=until:raise TimeoutError('Absolute configuration deadline expired')
    within();write_event({'phase':'intent','request_hex':packet.hex()});within()
    sent=0;raw=bytearray()
    while sent<len(packet):
        within();n=transport.write(packet[sent:],until)
        if type(n) is not int or not 0<n<=len(packet)-sent:raise ValueError('Invalid write progress')
        sent+=n;write_event({'phase':'sent','bytes':sent});within()
    while len(raw)<128:
        within();chunk=transport.read(128-len(raw),until)
        if not isinstance(chunk,bytes):raise ValueError('Invalid read type')
        raw.extend(chunk);write_event({'phase':'prefix','response_hex':raw.hex()});within()
        if not chunk or len(raw)>128:raise ValueError('Empty/overlong configuration reply')
    result=response(bytes(raw),image_hash=image_hash,source_hash=source_hash,nonce=nonce)
    within();write_event({'phase':'validated','receipt':result});within()
    return result
