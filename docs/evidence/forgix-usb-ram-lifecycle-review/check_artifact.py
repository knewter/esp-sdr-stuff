"""Read local build exports and mutate only memory; no loader or device access."""
import importlib.util
import json
from pathlib import Path
import struct
import sys

source_root, artifact_root = (Path(p).resolve() for p in sys.argv[1:3])
sys.path.insert(0,str(source_root/'tools'))
spec=importlib.util.spec_from_file_location('reviewed_lifecycle',source_root/'tools/forgix_usb_ram_trial.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
artifact=m.artifact_check(artifact_root)
raw=(artifact_root/'forgix_usb_ram.elf').read_bytes()
layout=m.inspect_elf(raw)
bad=bytearray(raw)
program_header_offset=struct.unpack_from('<I',bad,28)[0]
program_header_size, program_header_count=struct.unpack_from('<HH',bad,42)
load_header=next(program_header_offset+i*program_header_size for i in range(program_header_count)
                 if struct.unpack_from('<I',bad,program_header_offset+i*program_header_size)[0]==1)
struct.pack_into('<I',bad,load_header+12,0x10000000)
try:
    m.inspect_elf(bytes(bad))
except ValueError:
    flash_rejected=True
else:
    flash_rejected=False
assert flash_rejected, 'A mutated flash/XIP physical destination was accepted'
assert artifact['elf_sha256']==m.ELF_SHA and artifact['build_source_sha256']==m.PROFILE_SOURCE_SHA
print(json.dumps({'hardware_opened':False,'exact_historical_artifact_admitted':True,
                  'allocated_load_bytes':layout['allocated_load_bytes'],'stack_bytes':layout['stack_bytes'],
                  'heap_section_bytes':layout['heap_section_bytes'],'flash_destination_mutation_rejected':flash_rejected,
                  'elf_sha256':artifact['elf_sha256'],'build_source_sha256':artifact['build_source_sha256']}))
