#!/usr/bin/env python3
"""Validate the separate register diagnostic artifact without opening hardware."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import struct
import subprocess

import build_esp_register_observation as build
from build_esp_sdr_uart import SDK_NIX_SOURCE_HASH

ROOT = build.ROOT
FLASH = {'flash_mode':'dio','flash_freq':'40m','flash_size':'2MB'}
# Pinned SDK components/heap/port/esp32/memory_layout.c maps these two
# MAC-dump banks to I-port pools 8 and 7, respectively (lines 92-93).
RESERVED = ((0x3ffe8000,0x3fff8000),(0x400a8000,0x400b8000))
DEFAULTS_SHA = 'd417261421a976fbf99e91c11fc65a179d0eaaba289e6c1ec21c84e88be8ef8e'
PROFILE_SHA = '7166ca2d14278c98b181edac8d455c2e459062793b1edb262e8d2a49eb999fd6'


class ArtifactError(ValueError): pass


def require(condition,message):
    if not condition: raise ArtifactError(message)


def typed_equal(left,right):
    if type(left) is not type(right): return False
    if isinstance(left,dict): return left.keys()==right.keys() and all(typed_equal(left[k],right[k]) for k in left)
    if isinstance(left,list): return len(left)==len(right) and all(typed_equal(a,b) for a,b in zip(left,right))
    return left==right


def json_read(path):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'Duplicate JSON key')
            result[key]=value
        return result
    return json.loads(path.read_text(),object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ArtifactError('Nonfinite JSON')))


def private_file(root,name):
    path=root/name
    require(not path.is_symlink() and path.resolve().is_relative_to(root),'Artifact symlink/path escape')
    require(stat.S_ISREG(path.stat().st_mode) and path.stat().st_mode&0o077==0,'Artifact file must be private and regular')
    return path


def partition_check(raw):
    require(len(raw)==3072,'Partition table must be 3072 bytes')
    expected=((1,2,0x9000,0x6000,b'nvs'),(1,1,0xf000,0x1000,b'phy_init'),(0,0,0x10000,0x100000,b'factory'))
    for n,fields in enumerate(expected):
        magic,kind,subtype,offset,size,label,flags=struct.unpack_from('<HBBII16sI',raw,n*32)
        label_expected=fields[-1].ljust(16,b'\0')
        require(magic==0x50aa and flags==0 and (kind,subtype,offset,size)==fields[:-1] and label==label_expected,
                'Noncanonical diagnostic partition layout')
    require(raw[96:112]==b'\xeb\xeb'+b'\xff'*14 and raw[112:128]==hashlib.md5(raw[:96]).digest(),
            'Partition MD5 mismatch')
    require(raw[128:]==b'\xff'*(len(raw)-128),'Extra partition/signature data')


def flasher_check(data):
    expected={'write_flash_args':['--flash-mode','dio','--flash-size','2MB','--flash-freq','40m'],
        'flash_settings':FLASH,'flash_files':{'0x1000':'bootloader/bootloader.bin','0x8000':'partition_table/partition-table.bin','0x10000':'esp_sdr.bin'},
        'bootloader':{'offset':'0x1000','file':'bootloader/bootloader.bin','encrypted':'false'},
        'partition-table':{'offset':'0x8000','file':'partition_table/partition-table.bin','encrypted':'false'},
        'app':{'offset':'0x10000','file':'esp_sdr.bin','encrypted':'false'},
        'extra_esptool_args':{'after':'hard-reset','before':'default-reset','stub':True,'chip':'esp32'}}
    require(typed_equal(data,expected),'Unexpected generated flash arguments')


def excluded_range(address,size):
    require(type(address) is int and type(size) is int and 0<=address<2**32 and 0<=size and address+size<=2**32,
            'Invalid allocated address/size')
    require(not any(size and address<hi and address+size>lo for lo,hi in RESERVED),
            'Allocated memory overlaps MAC sample slab or instruction alias')


def elf_check(raw):
    """Read ELF32 section/program/symbol tables directly; no host toolchain needed."""
    def area(offset,size):
        require(0<=offset<=len(raw) and 0<=size<=len(raw)-offset,'Truncated ELF structure')
        return raw[offset:offset+size]
    h=struct.unpack('<16sHHIIIIIHHHHHH',area(0,52))
    ident,kind,machine,version,entry,phoff,shoff,_,ehsize,phsize,phnum,shsize,shnum,shstrings=h
    require(ident[:7]==b'\x7fELF\x01\x01\x01' and kind==2 and machine==94 and version==1 and ehsize==52,
            'Expected executable little-endian ELF32 Xtensa image')
    require(shsize==40 and 1<=shnum<=4096 and shstrings<shnum and phsize==32 and 1<=phnum<=128,'Invalid ELF tables')
    sections=[struct.unpack('<10I',area(shoff+i*40,40)) for i in range(shnum)]
    names_section=sections[shstrings];require(names_section[1]==3,'ELF section names table missing')
    names=area(names_section[4],names_section[5])
    def cstring(data,offset):
        require(0<=offset<len(data) and b'\0' in data[offset:],'Invalid ELF string offset')
        return data[offset:data.index(b'\0',offset)].decode('ascii')
    alloc=[];found={};entry_valid=False
    for s in sections:
        name,stype,flags,address,offset,size,link,_,align,entsize=s
        section_name=cstring(names,name)
        if stype!=8: area(offset,size)
        if flags&2 and size:
            excluded_range(address,size)
            require(not align or not (align&(align-1)),'Invalid ELF alignment')
            alloc.append((address,address+size,section_name))
            entry_valid |= bool(flags&4 and address<=entry<address+size)
        if stype==2:
            require(entsize==16 and size%16==0 and link<shnum and sections[link][1]==3,'Invalid ELF symbols')
            strings=area(sections[link][4],sections[link][5])
            for pos in range(offset,offset+size,16):
                name,value,length,info,other,index=struct.unpack('<IIIBBH',area(pos,16))
                symbol=cstring(strings,name)
                if symbol not in build.BUFFER_SYMBOLS: continue
                require(symbol not in found and index<shnum and info&15==1 and other==0,'Invalid/duplicate diagnostic ELF symbol')
                owner=sections[index]
                require(owner[2]&3==3 and owner[3]<=value<value+length<=owner[3]+owner[5],
                        'Diagnostic symbol not contained in writable allocated section')
                found[symbol]={'address':value,'size':length,'end':value+length}
    alloc.sort()
    require(all(a[1]<=b[0] for a,b in zip(alloc,alloc[1:])),'Overlapping allocated ELF sections')
    require(entry_valid,'ELF entrypoint is outside executable section')
    for i in range(phnum):
        ptype,offset,vaddr,paddr,filesz,memsz,_,align=struct.unpack('<8I',area(phoff+i*32,32))
        if ptype==1:
            require(filesz<=memsz,'Invalid ELF load size');area(offset,filesz)
            excluded_range(vaddr,memsz);excluded_range(paddr,memsz)
    nm='\n'.join(f"{v['address']:08x} {v['size']:08x} B {k}" for k,v in found.items())
    require(typed_equal(build.validate_symbols(nm),found),'Diagnostic ELF buffer mismatch')
    return found,entry


def map_check(text,buffers):
    # Require actual per-object section allocations and symbol addresses, not
    # just the cross-reference list or manifest's claimed addresses.
    for name,data in buffers.items():
        allocations=re.findall(r'^ \.bss\.'+re.escape(name)+r'\s*\n?\s*(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+[^\n]*receiver\.c\.obj\)',text,re.M)
        definitions=re.findall(r'^\s*(0x[0-9a-f]+)\s+'+re.escape(name)+r'\s*$',text,re.M)
        require(len(allocations)==len(definitions)==1 and int(allocations[0][0],16)==int(definitions[0],16)==data['address']
                and int(allocations[0][1],16)==data['size'],'Linker map disagrees with diagnostic ELF allocation')


def image_check(raw,application=False,elf_hash=None,elf_entry=None):
    from esptool.bin_image import ESP32FirmwareImage
    require(len(raw)>=24 and raw[0]==0xe9 and 1<=raw[1]<=16 and raw[2:4]==b'\x02\x10'
            and raw[12:14]==b'\0\0','Image target or DIO/40 MHz/2 MB header differs')
    image=ESP32FirmwareImage(io.BytesIO(raw))
    require(image.checksum==image.calculate_checksum() and image.append_digest and image.stored_digest==image.calc_digest,
            'Image checksum or SHA256 footer mismatch')
    require(image.data_length+32==len(raw),'Unexpected trailing image data/signature')
    # ESP32-D0WD-V3 rev3.1 must be inside the declared revision range.
    require(raw[14]<=3 and int.from_bytes(raw[15:17],'little')<=301<=int.from_bytes(raw[17:19],'little'),
            'Image chip revision excludes preserved ESP32 rev3.1')
    # Bootloader uses temporary DRAM in a sample bank before the receiver runs;
    # its bytes still require exact checksums/header/layout. Only application
    # allocations coexist with the active MAC dump and must exclude both aliases.
    if application:
        for segment in image.segments: excluded_range(segment.addr,len(segment.data))
    if application:
        require(image.entrypoint==elf_entry,'Image and ELF entrypoints differ')
        descriptor=raw[32:288]
        require(len(descriptor)==256 and descriptor[:4]==struct.pack('<I',0xabcd5432) and descriptor[4:16]==b'\0'*12,
                'Application descriptor/security version differs')
        require(descriptor[16:48]==build.VERSION.encode().ljust(32,b'\0') and descriptor[48:80]==b'esp_sdr'.ljust(32,b'\0'),
                'Application identity/version differs')
        require(descriptor[112:144].split(b'\0')[0]==b'v6.2.0' and descriptor[144:176]==bytes.fromhex(elf_hash),
                'Application SDK/ELF descriptor differs')
    return image


def sdk_check(provenance):
    require(type(provenance) is dict and provenance.get('revision')==build.SDK and provenance.get('source_hash')==SDK_NIX_SOURCE_HASH,
            'SDK source revision/hash is unpinned')
    for key in ('idf_path','source_path'):
        value=provenance.get(key)
        require(type(value) is str and re.fullmatch(r'/nix/store/[a-z0-9]{32}-[^/]+',value) and Path(value).is_dir(),
                'SDK paths must exist as immutable Nix store outputs')
    actual=subprocess.check_output(['nix','--extra-experimental-features','nix-command','hash','path','--sri',provenance['source_path']],
                                   text=True,timeout=60).strip()
    require(actual==SDK_NIX_SOURCE_HASH,'Actual SDK source NAR differs from pinned fixed-output hash')


def elf_image_check(elf_raw,image):
    """Independently bind loaded application bytes to the exported linked ELF."""
    from esptool.bin_image import ELFFile
    elf=ELFFile(elf_raw);sections=[]
    for section in elf.sections:
        if not section.flags&2: continue
        data=section.data
        if section.name=='.flash.appdesc':
            require(data[144:176]==b'\0'*32,'ELF descriptor hash slot was not initially zero')
            data=data[:144]+hashlib.sha256(elf_raw).digest()+data[176:]
        sections.append((section.addr,data))
    ranges=sorted((segment.addr,segment.addr+len(segment.data)) for segment in image.segments if segment.addr)
    require(all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])),'Overlapping application image segments')
    for address,data in sections:
        covered=0
        for segment in image.segments:
            lo=max(address,segment.addr);hi=min(address+len(data),segment.addr+len(segment.data))
            if lo<hi:
                require(segment.data[lo-segment.addr:hi-segment.addr]==data[lo-address:hi-address],
                        'Application section bytes differ from linked ELF')
                covered+=hi-lo
        require(covered==len(data),'Linked ELF section missing from application image')
    for segment in image.segments:
        expected=bytearray(len(segment.data))
        for address,data in sections:
            lo=max(address,segment.addr);hi=min(address+len(data),segment.addr+len(segment.data))
            if lo<hi: expected[lo-segment.addr:hi-segment.addr]=data[lo-address:hi-address]
        require(segment.data==expected,'Application image contains non-ELF loaded bytes')


def validate_artifact(artifact,manifest):
    artifact=Path(artifact).resolve();manifest=Path(manifest).resolve()
    require(artifact.is_relative_to(ROOT/'.scratch') and artifact!=ROOT/'.scratch' and manifest==artifact/'manifest.json',
            'Diagnostic artifacts must be private ignored .scratch outputs')
    require(artifact.stat().st_mode&0o077==0,'Artifact directory must be private')
    subprocess.run(['git','-C',str(ROOT),'check-ignore','--quiet',str(artifact)],check=True,capture_output=True)
    data=json_read(private_file(artifact,'manifest.json'));info=json_read(private_file(artifact,'build-info.json'))
    require(type(data) is dict and type(info) is dict,'Manifest/build-info must be objects')
    for key,value in [('schema',1),('kind',build.KIND),('target','esp32'),('version',build.VERSION)]:
        require(typed_equal(data.get(key),value) and (key=='schema' or typed_equal(info.get(key),value)), 'Explicit diagnostic identity required')
    files,profile=build.source_files()
    require(files['profile.json']==PROFILE_SHA,'Fixed diagnostic profile bytes changed')
    require(data.get('info')==info.get('info')==profile['info'] and typed_equal(info.get('profile'),profile),'Diagnostic INFO/profile differs')
    require(data.get('build_info_sha256')==build.sha(artifact/'build-info.json'),'Build-info hash mismatch')
    require(typed_equal(info.get('source_files'),files) and data.get('source_tree_sha256')==info.get('source_tree_sha256')==build.tree_hash(files),
            'Artifact differs from current diagnostic source')
    revision=info.get('source_commit');require(type(revision) is str and re.fullmatch('[0-9a-f]{40}',revision),'Missing source commit')
    inputs={f'firmware/register-observation/{name}':digest for name,digest in files.items()}
    inputs['tools/build_esp_register_observation.py']=build.sha(Path(build.__file__))
    require(info.get('builder_sha256')==inputs['tools/build_esp_register_observation.py'],'Builder bytes differ')
    for path,digest in inputs.items():
        committed=subprocess.check_output(['git','-C',str(ROOT),'show',revision+':'+path],timeout=10)
        current=subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+path],timeout=10)
        require(hashlib.sha256(committed).hexdigest()==hashlib.sha256(current).hexdigest()==digest,'Diagnostic build inputs must match recorded and current commits')
    require(info.get('source_base_revision')==build.BASE and info.get('idf_commit')==build.SDK,'Source base/SDK pins differ')
    overlay=build.load_overlay();prepared=info.get('prepared_source',{})
    require(prepared.get('receiver_sha256')==hashlib.sha256(overlay.receiver_text().encode()).hexdigest() and
            prepared.get('transport_sha256')==hashlib.sha256(overlay.transport_text().encode()).hexdigest() and
            prepared.get('defaults_sha256')==DEFAULTS_SHA and len(prepared.get('receiver_submodules',[]))==1 and
            re.fullmatch(r'a53a0756833c045311ea1d79a2badf495cdfde4c components/esp-dsp(?: \([^\n]+\))?',prepared['receiver_submodules'][0]),
            'Prepared receiver/transport/defaults/submodule differ')
    require(typed_equal(data.get('flash_settings'),FLASH),'Manifest flash settings differ')
    for name,key in [('sdkconfig','sdkconfig_sha256'),('esp_sdr.elf','elf_sha256'),('linker.map','linker_map_sha256'),
                     ('symbols.txt','symbols_sha256'),('flasher_args.json','flasher_args_sha256')]:
        require(build.sha(private_file(artifact,name))==info.get(key),'Artifact '+name+' hash mismatch')
    try: build.validate_config((artifact/'sdkconfig').read_text())
    except ValueError as error: raise ArtifactError(str(error)) from error
    require(typed_equal(info.get('required_sdkconfig_lines'),list(build.REQUIRED)) and
            typed_equal(info.get('disabled_hidden_sdkconfig_keys'),list(build.DISABLED_HIDDEN)),'Configuration policy differs')
    buffers,entry=elf_check((artifact/'esp_sdr.elf').read_bytes())
    require(typed_equal(info.get('linked_buffers'),buffers) and typed_equal(build.validate_symbols((artifact/'symbols.txt').read_text()),buffers),
            'Recorded/nm allocations disagree with ELF')
    map_check((artifact/'linker.map').read_text(),buffers);flasher_check(json_read(artifact/'flasher_args.json'))
    require(type(data.get('parts')) is list and len(data['parts'])==3,'Unexpected part count')
    for part,(name,offset,end) in zip(data['parts'],build.PARTS):
        require(type(part) is dict and set(part)=={'name','offset','size','sha256'} and part.get('name')==name and
                type(part.get('offset')) is int and part['offset']==offset and type(part.get('size')) is int and 0<part['size']<=end-offset,
                'Unexpected part identity/layout/size')
        path=private_file(artifact,'esp32/'+name)
        require(path.stat().st_size==part['size'] and build.sha(path)==part['sha256'],'Part size/hash mismatch')
        if name=='partition-table.bin': partition_check(path.read_bytes())
        else:
            image=image_check(path.read_bytes(),name=='esp_sdr.bin',info['elf_sha256'],entry)
            if name=='esp_sdr.bin': elf_image_check((artifact/'esp_sdr.elf').read_bytes(),image)
    sdk_check(info.get('nix_sdk_provenance'))
    return data,info


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,required=True);parser.add_argument('--manifest',type=Path)
    args=parser.parse_args(argv)
    manifest,info=validate_artifact(args.artifact,args.manifest or args.artifact/'manifest.json')
    print(json.dumps({'kind':build.KIND,'status':'artifact_validated','version':build.VERSION,
                      'manifest_sha256':build.sha(args.artifact/'manifest.json'),'source_commit':info['source_commit']}))


if __name__=='__main__': main()
