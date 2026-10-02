"""Synthetic, hardware-free artifact mutations; no receiver is installed."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import esp_register_artifact as guard
import build_esp_register_observation as build


def digest(data): return hashlib.sha256(data).hexdigest()


def elf_fixture():
    """Minimal independently encoded ELF32 Xtensa executable, not compiler proof."""
    strings=b'\0regobs_wire\0regobs_json\0regobs_records\0'
    names=b'\0.shstrtab\0.strtab\0.symtab\0.iram0.text\0.dram0.bss\0.flash.appdesc\0'
    wire=0x3ffb4000;buffers={'regobs_wire':{'address':wire,'size':2048,'end':wire+2048},
        'regobs_json':{'address':wire+2048,'size':2048,'end':wire+4096},
        'regobs_records':{'address':wire+4096,'size':1944,'end':wire+6040}}
    data=bytearray(84);positions=[]
    for blob in (names,strings,b'\0'*16+b''.join(struct.pack('<IIIBBH',strings.index(name.encode()),v['address'],v['size'],1,0,5)
                                              for name,v in buffers.items()),b'\x11'*16,descriptor_fixture()):
        positions.append(len(data));data.extend(blob)
    shoff=len(data);table=[(0,0,0,0,0,0,0,0,0,0),
        (names.index(b'.shstrtab'),3,0,0,positions[0],len(names),0,0,1,0),
        (names.index(b'.strtab'),3,0,0,positions[1],len(strings),0,0,1,0),
        (names.index(b'.symtab'),2,0,0,positions[2],64,2,1,4,16),
        (names.index(b'.iram0.text'),1,6,0x40080000,positions[3],16,0,0,4,0),
        (names.index(b'.dram0.bss'),8,3,wire,0,6040,0,0,8,0),
        (names.index(b'.flash.appdesc'),1,2,0x3f400020,positions[4],256,0,0,4,0)]
    for row in table:data.extend(struct.pack('<10I',*row))
    data[:52]=struct.pack('<16sHHIIIIIHHHHHH',b'\x7fELF\x01\x01\x01'+b'\0'*9,2,94,1,0x40080000,52,shoff,0,52,32,1,40,7,1)
    data[52:84]=struct.pack('<8I',1,positions[3],0x40080000,0x40080000,16,16,5,4)
    return bytes(data),buffers


def descriptor_fixture(elf_hash=None,version=b'regobs-v1'):
    descriptor=bytearray(256);struct.pack_into('<I',descriptor,0,0xabcd5432)
    descriptor[16:48]=version.ljust(32,b'\0');descriptor[48:80]=b'esp_sdr'.ljust(32,b'\0')
    descriptor[112:144]=b'v6.2.0'.ljust(32,b'\0')
    if elf_hash:descriptor[144:176]=bytes.fromhex(elf_hash)
    return bytes(descriptor)


def image_fixture(elf_hash=None,version=b'regobs-v1'):
    """Encode the documented ESP32 header, segment XOR and SHA footer directly."""
    entry=0x40080000 if elf_hash else 0x40078000
    segments=[(entry,b'\x11'*16)]
    if elf_hash:
        segments.insert(0,(0x3f400020,descriptor_fixture(elf_hash,version)))
    data=bytearray(24);struct.pack_into('<BBBBI',data,0,0xe9,len(segments),2,0x10,entry)
    data[8]=0xee;struct.pack_into('<H',data,17,399);data[23]=1
    checksum=0xef
    for address,body in segments:
        data.extend(struct.pack('<II',address,len(body)));data.extend(body)
        for byte in body:checksum^=byte
    data.extend(b'\0'*((15-len(data)%16)%16));data.append(checksum)
    data.extend(hashlib.sha256(data).digest());return bytes(data)


def partition_fixture():
    data=b''.join(struct.pack('<HBBII16sI',0x50aa,*fields,0) for fields in (
        (1,2,0x9000,0x6000,b'nvs'.ljust(16,b'\0')),
        (1,1,0xf000,0x1000,b'phy_init'.ljust(16,b'\0')),
        (0,0,0x10000,0x100000,b'factory'.ljust(16,b'\0'))))
    return data+b'\xeb\xeb'+b'\xff'*14+hashlib.md5(data).digest()+b'\xff'*(3072-128)


FLASH_ARGS={'write_flash_args':['--flash-mode','dio','--flash-size','2MB','--flash-freq','40m'],
    'flash_settings':{'flash_mode':'dio','flash_freq':'40m','flash_size':'2MB'},
    'flash_files':{'0x1000':'bootloader/bootloader.bin','0x8000':'partition_table/partition-table.bin','0x10000':'esp_sdr.bin'},
    'bootloader':{'offset':'0x1000','file':'bootloader/bootloader.bin','encrypted':'false'},
    'partition-table':{'offset':'0x8000','file':'partition_table/partition-table.bin','encrypted':'false'},
    'app':{'offset':'0x10000','file':'esp_sdr.bin','encrypted':'false'},
    'extra_esptool_args':{'after':'hard-reset','before':'default-reset','stub':True,'chip':'esp32'}}


class ComponentTests(unittest.TestCase):
    def test_actual_binary_structure_and_footer_mutations(self):
        elf,buffers=elf_fixture();self.assertEqual(guard.elf_check(elf),(buffers,0x40080000))
        good=image_fixture(digest(elf));guard.image_check(good,True,digest(elf),0x40080000)
        for offset in (2,3,12,35,100,len(good)-1):
            bad=bytearray(good);bad[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(Exception):guard.image_check(bytes(bad),True,digest(elf),0x40080000)
        with self.assertRaises(guard.ArtifactError):guard.image_check(image_fixture(digest(elf),b'550fade-uart921600'),True,digest(elf),0x40080000)
        with self.assertRaises(guard.ArtifactError):guard.image_check(good+b'\0'*16,True,digest(elf),0x40080000)

    def test_rehashed_valid_image_must_still_match_elf_code_bytes(self):
        elf,_=elf_fixture();raw=image_fixture(digest(elf));image=guard.image_check(raw,True,digest(elf),0x40080000)
        guard.elf_image_check(elf,image)
        # Make different executable bytes with entirely valid new XOR/SHA.
        forged=bytearray(raw);code_offset=24+8+256+8;forged[code_offset]^=1
        forged[-33]^=1;forged[-32:]=hashlib.sha256(forged[:-32]).digest()
        image=guard.image_check(bytes(forged),True,digest(elf),0x40080000)
        with self.assertRaises(guard.ArtifactError):guard.elf_image_check(elf,image)

    def test_elf_section_symbol_and_instruction_alias_bounds(self):
        elf,_=elf_fixture();shoff=struct.unpack_from('<I',elf,32)[0]
        for position,value in ((18,243),(shoff+5*40+12,0x3ffe8000),(shoff+4*40+12,0x400b0000),
                               (shoff+3*40+36,8),(shoff+5*40+8,2),(52+20,0xffffffff)):
            bad=bytearray(elf)
            struct.pack_into('<H' if position==18 else '<I',bad,position,value)
            with self.subTest(position=position),self.assertRaises((guard.ArtifactError,ValueError)):guard.elf_check(bytes(bad))
        for address,size in ((0x3ffe7fff,2),(0x400a8000,1),(0x400b7fff,2),(0xfffffff0,32)):
            with self.assertRaises(guard.ArtifactError):guard.excluded_range(address,size)
        guard.excluded_range(0x40080000,0x20000)

    def test_canonical_partition_md5_flags_extra_and_layout(self):
        raw=partition_fixture();guard.partition_check(raw)
        for offset in (0,4,12,28,96,112,128):
            data=bytearray(raw);data[offset]^=1
            with self.subTest(offset=offset),self.assertRaises(guard.ArtifactError):guard.partition_check(bytes(data))
        data=bytearray(raw);struct.pack_into('<I',data,64+8,0x110000);data[112:128]=hashlib.md5(data[:96]).digest()
        with self.assertRaises(guard.ArtifactError):guard.partition_check(bytes(data))

    def test_flash_args_security_target_and_boolean_types(self):
        guard.flasher_check(FLASH_ARGS)
        for path,value in ((('app','encrypted'),'true'),(('app','offset'),'0x20000'),
                           (('extra_esptool_args','chip'),'esp32s3'),(('extra_esptool_args','stub'),1)):
            data=copy.deepcopy(FLASH_ARGS);data[path[0]][path[1]]=value
            with self.assertRaises(guard.ArtifactError):guard.flasher_check(data)

    def test_sdk_actual_nar_not_just_claimed_hash(self):
        provenance={'revision':build.SDK,'source_hash':guard.SDK_NIX_SOURCE_HASH,
            'source_path':'/nix/store/'+'a'*32+'-source','idf_path':'/nix/store/'+'b'*32+'-esp-idf'}
        with patch.object(Path,'is_dir',return_value=True),patch.object(guard.subprocess,'check_output',return_value='sha256-wrong\n') as call:
            with self.assertRaises(guard.ArtifactError):guard.sdk_check(provenance)
            self.assertIn('hash',call.call_args.args[0]);self.assertIn(provenance['source_path'],call.call_args.args[0])
        with patch.object(Path,'is_dir',return_value=True),patch.object(guard.subprocess,'check_output',return_value=guard.SDK_NIX_SOURCE_HASH+'\n'):
            guard.sdk_check(provenance)
            with self.assertRaises(guard.ArtifactError):guard.sdk_check({**provenance,'revision':'0'*40})


class WholeArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.artifact=self.root/'.scratch/artifact'
        self.artifact.mkdir(parents=True,mode=0o700);(self.artifact/'esp32').mkdir(mode=0o700)
        self.elf,self.buffers=elf_fixture();files,profile=build.source_files();overlay=build.load_overlay()
        self.info={'kind':build.KIND,'target':'esp32','version':build.VERSION,'info':profile['info'],
            'source_commit':'1'*40,'source_base_revision':build.BASE,'source_files':files,'source_tree_sha256':build.tree_hash(files),
            'builder_sha256':build.sha(Path(build.__file__)),'idf_commit':build.SDK,'nix_sdk_provenance':{'fixture_only':True},
            'required_sdkconfig_lines':list(build.REQUIRED),'disabled_hidden_sdkconfig_keys':list(build.DISABLED_HIDDEN),
            'profile':profile,'linked_buffers':self.buffers,'prepared_source':{
                'receiver_sha256':digest(overlay.receiver_text().encode()),'transport_sha256':digest(overlay.transport_text().encode()),
                'defaults_sha256':guard.DEFAULTS_SHA,'receiver_submodules':['a53a0756833c045311ea1d79a2badf495cdfde4c components/esp-dsp (a53a075)']}}
        self.manifest={'schema':1,'kind':build.KIND,'target':'esp32','version':build.VERSION,'info':profile['info'],
            'source_tree_sha256':build.tree_hash(files),'flash_settings':copy.deepcopy(guard.FLASH),'parts':[]}
        values={'esp_sdr.elf':self.elf,'sdkconfig':('\n'.join(build.REQUIRED)+'\n').encode(),
            'symbols.txt':''.join(f"{v['address']:08x} {v['size']:08x} B {k}\n" for k,v in self.buffers.items()).encode(),
            'linker.map':''.join(f" .bss.{k}\n 0x{v['address']:x} 0x{v['size']:x} esp-idf/main/libmain.a(receiver.c.obj)\n 0x{v['address']:x} {k}\n" for k,v in self.buffers.items()).encode(),
            'flasher_args.json':json.dumps(FLASH_ARGS).encode()}
        for name,value in values.items():self.write(name,value)
        for (name,offset,_),raw in zip(build.PARTS,(image_fixture(),partition_fixture(),image_fixture(digest(self.elf)))):
            self.write('esp32/'+name,raw);self.manifest['parts'].append({'name':name,'offset':offset,'size':len(raw),'sha256':digest(raw)})
        self.refresh()
        def committed(command,**kwargs):
            path=command[-1].split(':',1)[1]
            return (build.ROOT/path).read_bytes()
        self.patches=[patch.object(guard,'ROOT',self.root),patch.object(guard.subprocess,'run'),
                      patch.object(guard.subprocess,'check_output',side_effect=committed),patch.object(guard,'sdk_check')]
        for item in self.patches:item.start()

    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.temp.cleanup()

    def write(self,name,data):
        path=self.artifact/name;path.write_bytes(data);path.chmod(0o600)

    def refresh(self):
        for name,key in [('sdkconfig','sdkconfig_sha256'),('esp_sdr.elf','elf_sha256'),('linker.map','linker_map_sha256'),
                         ('symbols.txt','symbols_sha256'),('flasher_args.json','flasher_args_sha256')]:
            self.info[key]=build.sha(self.artifact/name)
        self.write('build-info.json',(json.dumps(self.info)+'\n').encode())
        self.manifest['build_info_sha256']=build.sha(self.artifact/'build-info.json')
        self.write('manifest.json',(json.dumps(self.manifest)+'\n').encode())

    def validate(self):return guard.validate_artifact(self.artifact,self.artifact/'manifest.json')

    def test_synthetic_complete_guard_and_no_hardware_entrypoint(self):
        data,info=self.validate();self.assertEqual(info['linked_buffers'],self.buffers)
        self.assertEqual(data['kind'],'esp32-register-observation-v1')
        import demo_esp_sdr
        with self.assertRaises(KeyError):demo_esp_sdr.receiver_profile(self.artifact,self.artifact/'manifest.json',921600)

    def test_source_old_revision_builder_and_profile_rehash_do_not_authorize(self):
        for key,value in [('source_files',{}),('source_base_revision','0'*40),('idf_commit','0'*40),
                          ('builder_sha256','0'*64),('profile',{**self.info['profile'],'gain_selector':47}),
                          ('linked_buffers',{**self.buffers,'regobs_wire':{**self.buffers['regobs_wire'],'address':0x3ffe8000}})]:
            old=self.info[key];self.info[key]=value;self.refresh()
            with self.subTest(key=key),self.assertRaises(guard.ArtifactError):self.validate()
            self.info[key]=old

    def test_manifest_rehash_cannot_authorize_security_map_flash_or_binary_mutations(self):
        original={name:(self.artifact/name).read_bytes() for name in ('sdkconfig','linker.map','flasher_args.json','esp32/esp_sdr.bin')}
        changes={'sdkconfig':original['sdkconfig']+b'CONFIG_SECURE_BOOT=y\n',
            'linker.map':original['linker.map'].replace(b'0x3ffb4000',b'0x3ffe8000'),
            'flasher_args.json':json.dumps({**FLASH_ARGS,'app':{**FLASH_ARGS['app'],'encrypted':'true'}}).encode(),
            'esp32/esp_sdr.bin':original['esp32/esp_sdr.bin'][:-1]+bytes([original['esp32/esp_sdr.bin'][-1]^1])}
        for name,data in changes.items():
            self.write(name,data)
            if name.startswith('esp32/'):self.manifest['parts'][-1]['sha256']=digest(data)
            self.refresh()
            with self.subTest(name=name),self.assertRaises(guard.ArtifactError):self.validate()
            self.write(name,original[name]);self.manifest['parts'][-1]['sha256']=digest(original['esp32/esp_sdr.bin'])

    def test_actual_git_commit_content_must_match_not_just_hex_revision(self):
        with patch.object(guard.subprocess,'check_output',return_value=b'wrong committed source'):
            with self.assertRaises(guard.ArtifactError):self.validate()

    def test_duplicate_json_private_permissions_escape_and_part_types(self):
        path=self.artifact/'manifest.json';original=path.read_bytes()
        self.write('manifest.json',original.replace(b'{',b'{"schema":1,',1))
        with self.assertRaises(guard.ArtifactError):self.validate()
        self.write('manifest.json',original);(self.artifact/'esp_sdr.elf').chmod(0o644)
        with self.assertRaises(guard.ArtifactError):self.validate()
        (self.artifact/'esp_sdr.elf').chmod(0o600)
        old=self.manifest['parts'][0]['offset'];self.manifest['parts'][0]['offset']=True;self.refresh()
        with self.assertRaises(guard.ArtifactError):self.validate()
        self.manifest['parts'][0]['offset']=old;self.refresh()
        (self.artifact/'esp_sdr.elf').unlink();(self.artifact/'esp_sdr.elf').symlink_to(self.root/'foreign.elf')
        (self.root/'foreign.elf').write_bytes(self.elf)
        with self.assertRaises(guard.ArtifactError):self.validate()


if __name__=='__main__':unittest.main()
