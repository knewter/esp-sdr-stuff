"""Exact observer-only image parser. Cannot accept old candidate profiles."""
import hashlib,json,re,subprocess,zlib
from pathlib import Path
import forgix_clock_candidate as compiler

def candidate(folder):
 root=compiler.b.ROOT;folder=Path(folder).absolute()
 compiler.b.require(folder.is_relative_to(root/'.scratch') and folder!=root/'.scratch' and '..' not in folder.parts,'Private observer candidate required')
 manifest=compiler.regular(folder/'result.json',256*1024).read_bytes();m=json.loads(manifest)
 for k,v in compiler.PROFILE.items():compiler.b.require(type(m.get(k)) is type(v) and m[k]==v,'Observer candidate profile differs')
 compiler.b.require(m.get('status')=='passed' and type(m.get('exit_code')) is int and m['exit_code']==0 and
  m.get('owned_process_group_closed') is True and m.get('private_generated_files_verified') is True,'Complete closed observer compiler required')
 revision=m.get('source_commit');fixed=m.get('source_sha256')
 compiler.b.require(type(revision) is str and re.fullmatch('[0-9a-f]{40}',revision) and type(fixed) is dict and set(fixed)==set(compiler.INPUTS),'Observer committed provenance required')
 for n,h in fixed.items():
  data=subprocess.check_output(['git','show',revision+':'+n],cwd=root,timeout=10)
  compiler.b.require(type(h) is str and re.fullmatch('[0-9a-f]{64}',h) and hashlib.sha256(data).hexdigest()==h,'Observer committed source differs')
 began=m.get('started_at_unix_ns');compiler.b.require(type(began) is int and began>0,'Observer acquisition time missing')
 for k,v in compiler.outputs(folder,began,fixed).items():compiler.b.require(m.get(k)==v,'Observer generated outputs differ')
 raw=compiler.regular(folder/'work/gateware/outflow'/(compiler.NAME+'.hex')).read_bytes()
 compiler.b.require(re.fullmatch(rb'(?:[0-9a-fA-F]{2}\n)+',raw) is not None,'Exact byte-per-line observer hex required')
 data=bytes.fromhex(raw.decode());compiler.b.require(0<len(data)<=196608,'Observer image bound192KiB')
 return data,{'kind':'forgix-clock-observer-exact-image','candidate_source_commit':revision,
  'candidate_manifest_sha256':hashlib.sha256(manifest).hexdigest(),'candidate_source_sha256':fixed,
  'hex_sha256':hashlib.sha256(raw).hexdigest(),'decoded_sha256':hashlib.sha256(data).hexdigest(),
  'decoded_bytes':len(data),'decoded_crc32':zlib.crc32(data),'physical_qualification_proved':False,'loading_admitted':False}
