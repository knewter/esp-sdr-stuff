"""Synthetic-only immutable host dispatch; daemon/kernel state is not frozen."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

TOOLS=('python','picotool','git','nix','nix-store','docker','task')
SOCKET='unix:///var/run/docker.sock'
SDK=Path('/nix/store/zzdqq5jiwbislr6v99spq09vmc9yiib1-pico-sdk-2.2.0-tinyusb-pinned')
COMPILER=Path('/nix/store/8im8fi1g72flhxjqarv43ykdcdjcl5sw-gcc-arm-embedded-15.3.rel1')

def require(value,message):
    if not value:raise ValueError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def store_root(path):
    path=Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'Absolute normalized runtime path required')
    require(len(path.parts)>=4 and path.parts[1:3]==('nix','store')
            and re.fullmatch(r'[0-9a-z]{32}-.+',path.parts[3]),'Nix-store runtime required')
    return Path(*path.parts[:4])

def executable(path):
    path=Path(path);store_root(path)
    resolved=path.resolve(strict=True);store_root(resolved)
    require(stat.S_ISREG(resolved.stat().st_mode) and os.access(path,os.X_OK),'Regular executable required')
    return {'path':str(path),'resolved_path':str(resolved),'sha256':sha(resolved)}

def endpoint():
    require(not any(os.environ.get(n) for n in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE',
        'GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_CONFIG_COUNT')),
        'Git source-identity overrides refuse')
    require(os.environ.get('DOCKER_HOST',SOCKET)==SOCKET,'Only reviewed local Docker socket allowed')
    require(not any(os.environ.get(n) for n in ('DOCKER_CONTEXT','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')),
            'Docker context/TLS overrides refuse')

def select():
    endpoint()
    return {n:executable(sys.executable if n=='python' else shutil.which(n) or '') for n in TOOLS}

def search_path(tools):
    return os.pathsep.join(dict.fromkeys(str(Path(tools[n]['path']).parent) for n in TOOLS))

def check_tools(tools,verify_bytes=True):
    require(type(tools) is dict and set(tools)==set(TOOLS),'Complete host tool tuple required')
    for name,row in tools.items():
        require(type(row) is dict and set(row)=={'path','resolved_path','sha256'} and type(row['path']) is str and type(row['resolved_path']) is str
                and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}',row['sha256']), 'Malformed executable tuple')
        if verify_bytes:require(executable(row['path'])==row,'Frozen host executable differs')
        else:
            store_root(row['path']);store_root(row['resolved_path'])
            require(str(Path(row['path']).resolve(strict=True))==row['resolved_path'],'Executable target differs')
    require(str(Path(sys.executable).resolve())==tools['python']['resolved_path'],'Current interpreter differs')

def activate(tools):
    """Before source/artifact queries; workers inherit this bounded search path."""
    check_tools(tools);endpoint()
    os.environ['PATH']=search_path(tools)
    os.environ['DOCKER_HOST']=SOCKET
    check_dispatch(tools)

def check_dispatch(tools,verify_bytes=True):
    check_tools(tools,verify_bytes);endpoint()
    require(os.environ.get('DOCKER_HOST')==SOCKET and os.environ.get('PATH')==search_path(tools),
            'Frozen host dispatch environment differs')
    for name in TOOLS[1:]:
        selected=shutil.which(name)
        require(selected is not None and selected==tools[name]['path'],
                'Host command shadowed or missing: '+name)

def paths(closure):
    if type(closure) is dict:rows=[dict(row,path=path) for path,row in closure.items()]
    else:
        require(type(closure) is list,'Nix closure metadata required');rows=closure
    require(0<len(rows)<=4096,'Bounded nonempty Nix closure required')
    result=set();references=set()
    for row in rows:
        require(type(row) is dict and type(row.get('path')) is str and type(row.get('narHash')) is str
                and re.fullmatch(r'sha256-[A-Za-z0-9+/]{43}=',row['narHash']),'Nix path/NAR metadata required')
        p=store_root(row['path']);require(str(p)==row['path'] and str(p) not in result,'Invalid/duplicate store root')
        result.add(str(p))
        refs=row.get('references')
        require(type(refs) is list and len(refs)<=4096,'Complete reference metadata required')
        checked=[]
        for ref in refs:
            require(type(ref) is str and str(store_root(ref))==ref,'Canonical referenced store root required')
            checked.append(ref)
        require(len(set(checked))==len(checked),'Duplicate store reference')
        references.update(checked)
    require(references<=result,'Incomplete transitive Nix reference graph')
    return result

def roots(tools,archive):
    return sorted({str(store_root(row[k])) for row in tools.values() for k in ('path','resolved_path')} |
                  {str(SDK),str(COMPILER),str(store_root(archive))})

def image_check(image_id,tools):
    # The caller must already have selected/activated tools before Git/artifact work.
    import forgix_usb_ram_trial as trial
    check_dispatch(tools)
    base=trial.image_check(tools['picotool']['path'],image_id)
    archive=Path(os.environ['PICOTOOL_USB_IMAGE']).resolve(strict=True)
    needed=roots(tools,archive)
    closure=json.loads(subprocess.check_output([tools['nix']['path'],'path-info','--json','--recursive',*needed],timeout=60))
    covered=paths(closure)
    require(set(needed)<=covered and paths(base['nix_recursive_closure'])<=covered,'Incomplete combined runtime closure')
    subprocess.run([tools['nix-store']['path'],'--verify-path',*sorted(covered)],check=True,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120)
    check_dispatch(tools)
    base.update(host_tools=tools,host_closure_roots=needed,host_nix_recursive_closure=closure,
                host_closure_contents_verified=True,host_dispatch_path=search_path(tools),
                docker_endpoint=SOCKET,host_trust_boundary='Docker/Nix daemons, kernel/udev/filesystem and pre-Python launcher remain trusted; selected Task is not ancestor invocation proof',
                image_archive_path=str(archive))
    check(base)
    return base

def check(environment,verify_bytes=True):
    require(type(environment) is dict and environment.get('host_closure_contents_verified') is True,
            'Verified host closure required')
    tools=environment.get('host_tools');check_dispatch(tools,verify_bytes)
    needed=roots(tools,environment['image_archive_path'])
    require(environment.get('host_closure_roots')==needed and environment.get('host_dispatch_path')==search_path(tools)
            and environment.get('docker_endpoint')==SOCKET,'Host dispatch binding differs')
    covered=paths(environment['host_nix_recursive_closure'])
    require(set(needed)<=covered and paths(environment['nix_recursive_closure'])<=covered,'Host closure does not cover runtime')
    for n in ('python','picotool'):
        require(environment[n+'_executable']==tools[n]['resolved_path']
                and environment[n+'_executable_sha256']==tools[n]['sha256'],'Runtime executable binding differs')
    if verify_bytes:
        require(sha(environment['image_archive_path'])==environment['image_archive_sha256'],'Frozen image archive differs')
