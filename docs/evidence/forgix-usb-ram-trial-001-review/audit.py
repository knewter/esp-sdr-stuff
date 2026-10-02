"""Audit retained files for the failed pre-load episode; never access devices."""
import argparse, hashlib, json, os, stat, subprocess, tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REV = '6e7b6bc617d855f38d0d62344ae939b8721c1cfe'
BASE = '72b6e55bb321e3d1c11fd7aea5a2db5eb361ec3824c53d564c12b3a0455f91b4'

def need(ok, label):
    if not ok: raise ValueError('Audit refused: '+label)

def digest(path):
    path = Path(path)
    need(stat.S_ISREG(path.stat().st_mode), 'non-file input')
    h = hashlib.sha256()
    with path.open('rb') as f:
        while part := f.read(1048576): h.update(part)
    return h.hexdigest()

def read(path): return json.loads(path.read_text())

def audit(p):
    s, pre = read(p/'session.json'), read(p/'preflight.json')
    need(s['status']=='failed' and s['failure_type']=='TimeoutExpired', 'terminal outcome')
    need(s['owned_hardware_processes_closed'] is True, 'owned closure not verified')
    need(0 < s['actual_hardware_session_seconds'] < 600, 'session budget')
    expected = {'session.json','preflight.json','before/initial-query-request.json',
                'before/usb-identity-private.json','before/initial-query.log'}
    need({str(x.relative_to(p)) for x in p.rglob('*') if x.is_file()}==expected, 'unexpected phase files')
    need(not any(k in s for k in ('before','after','capture')), 'unexpected completed phase')
    need(all(s[k]==pre[k] for k in ('binding','artifact','image','execution')), 'preflight/input continuity')
    frozen = s['execution']
    need(frozen['source_commit']==REV, 'execution revision')
    for name, expected_hash in frozen['inputs'].items():
        need(not Path(name).is_absolute() and '..' not in Path(name).parts, 'source path')
        blob = subprocess.check_output(['git','show',REV+':'+name],cwd=REPO)
        need(hashlib.sha256(blob).hexdigest()==expected_hash, 'frozen source hash')
    request, identity = read(p/'before/initial-query-request.json'), read(p/'before/usb-identity-private.json')
    target = request['target']
    need(request['label']=='initial' and target['pid']=='0009', 'selected factory query')
    need(target['serial_sha256']==identity['initial_serial_sha256']==s['binding']['uid_sha256'], 'private identity binding')
    need(target['bus']==identity['bus'] and target['address']==identity['initial_address'], 'selected enumeration binding')
    for path in s['binding']['baseline_paths']:
        need(Path(path).stat().st_size==2097152 and digest(path)==BASE, 'preserved original copy')
    a, image = s['artifact'], s['image']
    elf = Path(a['elf'])
    need(digest(elf)==a['elf_sha256'] and digest(elf.parent/'manifest.json')==a['manifest_sha256'], 'historical artifact hashes')
    build = read(elf.parent/'manifest.json')
    need(build['build_source_sha256']==a['build_source_sha256'], 'compiled source identity')
    need(digest(image['picotool_executable'])==image['picotool_executable_sha256'], 'picotool hash')
    need(digest(image['python_executable'])==image['python_executable_sha256'], 'Python hash')
    archive = Path(os.environ['PICOTOOL_USB_IMAGE'])
    need(digest(archive)==image['image_archive_sha256'], 'Nix archive hash')
    with tarfile.open(archive) as tar:
        rows = json.load(tar.extractfile('manifest.json'))
        need(len(rows)==1 and image['image_tag'] in rows[0]['RepoTags'], 'archive tag')
        image_id = 'sha256:'+hashlib.sha256(tar.extractfile(rows[0]['Config']).read()).hexdigest()
    need(image_id==image['image_id'] and image['closure_contents_verified'] is True and image['sdk_nar_verified'] is True, 'image/closure provenance')
    log = (p/'before/initial-query.log').read_text()
    need(all(t in log for t in ('port.open()', '_update_dtr_state', 'TIOCMBIC', '[Errno 110]', 'os.close', 'KeyboardInterrupt')), 'serial-open failure trace')
    return {'status':'independent_preload_failure_audit_passed','trial_status':'failed',
            'source_commit':REV,'source_artifact_image_bindings_verified':True,
            'image_id':image_id,'selected_private_identity_bound':True,
            'prior_original_copies_hash_verified':2,'prior_copy_bytes':2097152,
            'failure_stage':'initial_factory_serial_open_DTR_control','device_error_number':110,
            'outer_failure_type':'TimeoutExpired','hardware_session_s':s['actual_hardware_session_seconds'],
            'owned_process_group_closure_recorded':True,'independent_live_process_absence_checked':False,
            'ROM_or_RAM_load_step_recorded':False,
            'HELLO_STATUS_response_recorded':False,'capture_available':False,
            'CRC_payload_END_loss_or_throughput_result':None,
            'fresh_full_flash_or_factory_recovery_verified':False,
            'audit_hardware_or_Docker_access':False}

if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--session',required=True,type=Path)
    args=cli.parse_args()
    print(json.dumps(audit(args.session),indent=2))
