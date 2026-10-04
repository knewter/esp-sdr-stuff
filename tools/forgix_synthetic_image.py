"""Read-only exact synthetic compiler image binding; no programming admission."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zlib
import forgix_synthetic_candidate as compiler

def candidate(folder):
    root=compiler.b.ROOT;folder=Path(folder).absolute()
    compiler.b.require(folder.is_relative_to(root/'.scratch') and folder!=root/'.scratch' and '..' not in folder.parts,
                       'Private synthetic candidate directory required')
    manifest=compiler.regular(folder/'result.json',256*1024).read_bytes();m=json.loads(manifest)
    for key,value in compiler.PROFILE.items():
        compiler.b.require(type(m.get(key)) is type(value) and m[key]==value,'Synthetic candidate profile changed')
    compiler.b.require(m.get('status')=='passed' and type(m.get('exit_code')) is int and m['exit_code']==0 and
                       m.get('owned_process_group_closed') is True and m.get('private_generated_files_verified') is True,
                       'Complete closed synthetic compiler candidate required')
    revision=m.get('source_commit');fixed=m.get('source_sha256')
    compiler.b.require(type(revision) is str and re.fullmatch('[0-9a-f]{40}',revision) and type(fixed) is dict and
                       set(fixed)==set(compiler.INPUTS),'Synthetic source provenance required')
    for name,digest in fixed.items():
        compiler.b.require(type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest),'Invalid candidate source hash')
        blob=subprocess.check_output(['git','show',revision+':'+name],cwd=root,timeout=10)
        compiler.b.require(hashlib.sha256(blob).hexdigest()==digest,'Candidate committed source bytes changed')
    started=m.get('started_at_unix_ns')
    compiler.b.require(type(started) is int and started>0,'Candidate acquisition timestamp required')
    verified=compiler.verify_outputs(folder,started,fixed)
    for key,value in verified.items():compiler.b.require(m.get(key)==value,'Candidate output verification changed')
    raw=compiler.regular(folder/'work/gateware/outflow'/ (compiler.NAME+'.hex'),1024**2).read_bytes()
    compiler.b.require(re.fullmatch(rb'(?:[0-9a-fA-F]{2}\n)+',raw) is not None,'Exact Efinity byte-per-line hex required')
    data=bytes.fromhex(raw.decode('ascii'))
    compiler.b.require(0<len(data)<=196608,'Synthetic embedded image exceeds 192 KiB')
    return data,{'kind':'forgix-synthetic-exact-image','candidate_source_commit':revision,
        'candidate_manifest_sha256':hashlib.sha256(manifest).hexdigest(),'candidate_source_sha256':fixed,
        'hex_sha256':hashlib.sha256(raw).hexdigest(),'decoded_sha256':hashlib.sha256(data).hexdigest(),
        'decoded_bytes':len(data),'decoded_crc32':zlib.crc32(data),
        'physical_qualification_proved':False,'loading_admitted':False}

def wire_primitives(data):
    """Extract exact reviewed PIO functions, without the old serial dispatcher.

    Only three unused globals/profile declarations are removed. The caller
    redirects the request encoder by an explicit macro to its new finite map;
    the actual PIO body, pin ordering/guard and response parser stay unchanged.
    """
    text=data.decode('ascii');cut='int main(void) {'
    compiler.b.require(text.count(cut)==1,'Reviewed bridge main boundary changed')
    prefix=text.split(cut)[0]
    old='static bool configuration_attempted,configuration_ready;'
    compiler.b.require(prefix.count(old)==1,'Reviewed configuration state changed')
    prefix=prefix.replace(old,'static bool configuration_ready;')
    pattern=r'#ifdef BRIDGE_EMBEDDED_CONFIG\nconst char diagnostic_profile\[\].*?\n#endif\n'
    prefix,n=re.subn(pattern,'',prefix,flags=re.S)
    compiler.b.require(n==1,'Reviewed bridge profile changed')
    old='static uint8_t input[BRIDGE_REQUEST_BYTES],output[BRIDGE_RESPONSE_BYTES];\n'
    compiler.b.require(prefix.count(old)==1,'Reviewed bridge buffer state changed')
    return prefix.replace(old,'').encode('ascii')
