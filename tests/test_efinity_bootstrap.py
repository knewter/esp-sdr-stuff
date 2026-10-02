import contextlib
import importlib.util
import io
import json
import os
import signal
import stat
import subprocess
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import efinity_bootstrap as b

class Bootstrap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.oldmask=os.umask(0o077);self.store=b.Store(self.root)
        self.archive=self.root/'efinity-2026.1.132.tar.bz2'
    def tearDown(self):
        os.umask(self.oldmask);self.tmp.cleanup()
    def tar(self, members=None):
        members=members or {'efinity/2026.1.132/bin/setup.sh':b'# setup\n', 'efinity/2026.1.132/bin/python3':b'#!/bin/sh\nexit 0\n','efinity/2026.1.132/scripts/efx_run.py':b'# vendor\n','efinity/2026.1.132/scripts/sw_version.txt':b'2026.1.132\n'}
        with tarfile.open(self.archive,'w:bz2') as t:
            for name,data in members.items():
                m=tarfile.TarInfo(name);m.size=len(data);m.mode=0o755;t.addfile(m,io.BytesIO(data))
        return self.archive
    def install(self):
        self.tar()
        with self.store.locked():
            receipt=self.store.stage(self.archive,'full');return self.store.install(receipt['software_sha256'],'2026.1.132')
    def test_copy_idempotent_and_original_untouched(self):
        source=self.tar();before=source.read_bytes()
        with self.store.locked():
            first=self.store.stage(source,'full');second=self.store.stage(source,'full')
        self.assertFalse(first['reused']);self.assertTrue(second['reused']);self.assertEqual(source.read_bytes(),before)
        self.assertEqual((self.store.path/'archives'/first['software_sha256']/'download').stat().st_mode&0o777,0o600)
    def test_atomic_install_selection_and_reuse(self):
        first=self.install()
        with self.store.locked():second=self.store.install(None,'2026.1.132')
        self.assertFalse(first['reused']);self.assertTrue(second['reused']);installation,info=self.store.installed();self.assertTrue((installation/'bin/setup.sh').is_file());self.assertFalse(info['license_compile_verified'])
    def test_version_mismatch_retains_failed_unselected(self):
        self.tar()
        with self.store.locked():
            self.store.stage(self.archive,'full')
            with self.assertRaisesRegex(b.Refusal,'version differs'):self.store.install(None,'2026.1.999')
        self.assertFalse((self.store.path/'current.json').exists());self.assertEqual(len(list((self.store.path/'installs').glob('.failed-*'))),1)
    def test_existing_version_different_hash_refused(self):
        self.install();original=(self.store.path/'current.json').read_bytes();self.tar({'not-full':b'changed'})
        with self.store.locked():
            r=self.store.stage(self.archive,'full')
            with self.assertRaisesRegex(b.Refusal,'different archive'):self.store.install(r['software_sha256'],'2026.1.132')
        self.assertEqual((self.store.path/'current.json').read_bytes(),original)
    def test_partial_download_never_opened(self):
        f=self.root/'efinity.tar.bz2.crdownload';f.write_bytes(b'PRIVATE')
        with patch.object(Path,'open',side_effect=AssertionError('must not open')):
            with self.assertRaisesRegex(b.Refusal,'incomplete'):b.input_file(f)
    def test_bounded_discovery_alias_and_license_privacy(self):
        (self.root/'efinity-2026.1.tar.bz2').write_bytes(b'archive');(self.root/'Unconfirmed.crdownload').write_bytes(b'partial');(self.root/'efinity-license-PRIVATE-ID.lic').write_bytes(b'SECRET');(self.root/'unrelated').mkdir();(self.root/'unrelated/efinity-hidden.zip').write_bytes(b'ignore')
        alias=self.root/'alias';alias.symlink_to(self.root,target_is_directory=True)
        with patch.object(Path,'open',side_effect=AssertionError('discovery must not read')):r=b.discover([self.root,alias])
        self.assertEqual(len(r['candidates']),2);self.assertEqual(r['partial_downloads_not_opened'],1);self.assertNotIn('PRIVATE-ID',json.dumps(r));self.assertNotIn('SECRET',json.dumps(r))
    def test_opaque_license_copy_no_hash_or_identity(self):
        f=self.root/'efinity-private-ID.lic';f.write_bytes(b'SECRET-ID-CONTENTS')
        with self.store.locked():r=self.store.stage(f,'license');again=self.store.stage(f,'license')
        self.assertEqual(r,{'role':'license','reused':False});self.assertTrue(again['reused']);self.assertNotIn('SECRET',json.dumps(self.store.catalog()));self.assertNotIn('ID',json.dumps(self.store.catalog()))
    def test_license_destination_requires_safe_explicit_location(self):
        self.install();f=self.root/'input.lic';f.write_bytes(b'opaque');installation,_=self.store.installed()
        with self.store.locked():
            self.store.stage(f,'license')
            for destination in ('../outside','/tmp/license','scripts/efx_run.py','bin/setup.sh'):
                with self.assertRaises(b.Refusal):self.store.place_license(installation,destination)
            self.store.place_license(installation,'license/vendor.lic')
        self.assertEqual((installation/'license/vendor.lic').read_bytes(),b'opaque')
    def test_traversal_and_absolute_refusal_preserves_outside(self):
        outside=self.root/'outside';outside.write_bytes(b'ORIGINAL')
        for name in ('../outside','/tmp/outside','root/../../outside','root\\..\\outside'):
            self.tar({name:b'overwrite'})
            out=self.root/str(len(list(self.root.iterdir())));out.mkdir()
            with self.assertRaises(b.Refusal):b.extract(self.archive,out)
            self.assertEqual(outside.read_bytes(),b'ORIGINAL')
    def test_symlink_parent_or_escape_refused(self):
        for target,child in [('/etc',None),('../../outside',None),('inside','link/child')]:
            with tarfile.open(self.archive,'w:bz2') as t:
                m=tarfile.TarInfo('payload');m.size=1;t.addfile(m,io.BytesIO(b'x'));m=tarfile.TarInfo('link');m.type=tarfile.SYMTYPE;m.linkname=target;t.addfile(m)
                if child:m=tarfile.TarInfo(child);m.size=1;t.addfile(m,io.BytesIO(b'x'))
            out=self.root/str(len(list(self.root.iterdir())));out.mkdir()
            with self.assertRaises(b.Refusal):b.extract(self.archive,out)
    def test_safe_internal_relative_symlink(self):
        with tarfile.open(self.archive,'w:bz2') as t:
            m=tarfile.TarInfo('lib/actual');m.size=1;t.addfile(m,io.BytesIO(b'x'));m=tarfile.TarInfo('bin/link');m.type=tarfile.SYMTYPE;m.linkname='../lib/actual';t.addfile(m)
        out=self.root/'extract';out.mkdir();b.extract(self.archive,out);self.assertEqual((out/'bin/link').read_bytes(),b'x')
    def test_hardlink_special_duplicate_refusals(self):
        for mode in ('hard','fifo','duplicate'):
            with tarfile.open(self.archive,'w:bz2') as t:
                m=tarfile.TarInfo('item');m.type=tarfile.LNKTYPE if mode=='hard' else tarfile.FIFOTYPE if mode=='fifo' else tarfile.REGTYPE;m.linkname='target';t.addfile(m)
                if mode=='duplicate':t.addfile(m)
            out=self.root/mode;out.mkdir()
            with self.assertRaises(b.Refusal):b.extract(self.archive,out)
    def test_zip_full_extraction_and_paths(self):
        f=self.root/'full.zip'
        with zipfile.ZipFile(f,'w') as z:z.writestr('version/bin/file',b'bytes')
        out=self.root/'extract';out.mkdir();b.extract(f,out);self.assertEqual((out/'version/bin/file').read_bytes(),b'bytes')
        with zipfile.ZipFile(f,'w') as z:z.writestr('../outside',b'bytes')
        with self.assertRaises(b.Refusal):b.extract(f,out)
    def test_space_and_expanded_bounds(self):
        self.tar();out=self.root/'extract';out.mkdir()
        with patch.object(b.shutil,'disk_usage',return_value=type('Usage',(),{'free':0})()):
            with self.assertRaisesRegex(b.Refusal,'space'):b.extract(self.archive,out)
        with patch.object(b,'MAX_EXPANDED',1):
            with self.assertRaisesRegex(b.Refusal,'bound'):b.extract(self.archive,out)
    def test_patch_not_treated_as_full(self):
        self.tar()
        with self.store.locked():
            r=self.store.stage(self.archive,'patch')
            with self.assertRaisesRegex(b.Refusal,'not a full'):self.store.install(r['software_sha256'],'2026.1.132')
    def test_required_installed_file_mutation_refused(self):
        self.install();installation,_=self.store.installed();(installation/'scripts/efx_run.py').write_text('mutated')
        with self.assertRaisesRegex(b.Refusal,'bytes were changed'):self.store.installed()
    def test_runtime_failure_output_private_no_license_claim(self):
        self.install()
        def failing(command,**kwargs):
            kwargs['stdout'].write(b'SECRET LICENSE ID\n');return type('Result',(),{'returncode':7})()
        with patch.object(b.shutil,'which',return_value='/nix/store/fake/forgix-efinity'),patch.object(b,'run_owned',side_effect=lambda command,env,output,timeout,store: failing(command,stdout=output).returncode):r,code=b.runtime(self.store,'check',[])
        self.assertEqual(code,7);self.assertFalse(r['license_compile_verified']);self.assertNotIn('SECRET',json.dumps(r));self.assertEqual(len(list((self.store.path/'logs').glob('*.log'))),1)
    def test_current_symlink_and_store_parent_refused(self):
        self.install();current=self.store.path/'current.json';current.unlink();current.symlink_to(self.root/'secret')
        with self.assertRaises(b.Refusal):self.store.installed()
        other=self.root/'other';other.mkdir();(other/'.vendor').symlink_to(self.store.path)
        with self.assertRaises(b.Refusal):b.Store(other)

    def test_archives_parent_symlink_preserves_external_directory(self):
        self.tar();external=self.root/'external';external.mkdir();sentinel=external/'sentinel';sentinel.write_bytes(b'original')
        with self.store.locked():
            (self.store.path/'archives').symlink_to(external,target_is_directory=True)
            with self.assertRaisesRegex(b.Refusal,'symlink'):self.store.stage(self.archive,'full')
        self.assertEqual(list(external.iterdir()),[sentinel]);self.assertEqual(sentinel.read_bytes(),b'original')
    def test_existing_corrupt_other_version_preserves_current(self):
        first=self.install();prior=(self.store.path/'current.json').read_bytes()
        self.tar({'efinity/bin/setup.sh':b'# setup', 'efinity/bin/python3':b'python', 'efinity/scripts/efx_run.py':b'vendor', 'efinity/scripts/sw_version.txt':b'2026.2.1'})
        with self.store.locked():
            other=self.store.stage(self.archive,'full');self.store.install(other['software_sha256'],'2026.2.1')
            second,_=self.store.installed();(second/'scripts/efx_run.py').write_bytes(b'corrupt')
            b.save(self.store.path/'current.json',{'version':first['version'],'software_sha256':first['software_sha256']})
            with self.assertRaisesRegex(b.Refusal,'bytes were changed'):self.store.install(other['software_sha256'],'2026.2.1')
        self.assertEqual((self.store.path/'current.json').read_bytes(),prior)
    def test_source_growth_is_detected_before_unbounded_copy(self):
        f=self.root/'input';f.write_bytes(b'a'*10);g=b.file_chunks(f);self.assertEqual(next(g),b'a'*10)
        with f.open('ab') as out:out.write(b'changed')
        with self.assertRaisesRegex(b.Refusal,'grew'):next(g)
        before=f.stat();f.write_bytes(b'new')
        expected=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
        with self.assertRaisesRegex(b.Refusal,'changed before copying'):b.copy_frozen(f,self.root/'partial',expected=expected)
        self.assertEqual((self.root/'partial').stat().st_size,0)
    def test_zip_special_files_rejected(self):
        for kind in (stat.S_IFIFO,stat.S_IFCHR,stat.S_IFBLK,stat.S_IFSOCK):
            f=self.root/'special.zip';m=zipfile.ZipInfo('special');m.create_system=3;m.external_attr=(kind|0o600)<<16
            with zipfile.ZipFile(f,'w') as z:z.writestr(m,b'x')
            with self.assertRaisesRegex(b.Refusal,'special files'):
                with b.archive_entries(f):pass
    def test_tar_bound_checked_before_next_member(self):
        self.tar({'too-large':b'1234','next':b'z'})
        calls=[];original=tarfile.TarFile.next
        def step(t):
            result=original(t)
            if result is not None:calls.append(result.name)
            return result
        with patch.object(b,'MAX_EXPANDED',1),patch.object(tarfile.TarFile,'next',step):
            with self.assertRaisesRegex(b.Refusal,'bound'):
                with b.archive_entries(self.archive):pass
        self.assertTrue(calls);self.assertNotIn('next',calls) # no skip/decompression to second member
    def test_owned_timeout_closes_real_process_group(self):
        with self.store.locked(),(self.root/'log').open('wb') as log:
            with self.assertRaises(subprocess.TimeoutExpired):b.run_owned([sys.executable,'-c','import time; time.sleep(30)'],os.environ.copy(),log,.05,self.store)
        self.assertFalse((self.store.path/'runtime-unclosed.json').exists())
    def test_spawn_cancellation_registers_child_before_cleanup(self):
        proc=type('Proc',(),{'pid':123,'wait':lambda *a,**k:0})()
        def spawn(*a,**k):os.kill(os.getpid(),signal.SIGTERM);return proc
        with self.store.locked(),(self.root/'log').open('wb') as log,patch.object(b.subprocess,'Popen',side_effect=spawn),patch.object(b,'stop_group') as stop:
            with self.assertRaisesRegex(b.Refusal,'cancelled'):b.run_owned(['unused'],{},log,1,self.store)
        stop.assert_called_once_with(proc)
    def test_unclosed_group_blocks_further_storage_mutation(self):
        proc=type('Proc',(),{'pid':123,'wait':lambda *a,**k:0})()
        with self.store.locked(),(self.root/'log').open('wb') as log,patch.object(b.subprocess,'Popen',return_value=proc),patch.object(b,'stop_group',side_effect=b.Refusal('closure unknown')):
            with self.assertRaises(b.Refusal):b.run_owned(['unused'],{},log,1,self.store)
        with self.assertRaisesRegex(b.Refusal,'closure'):
            with self.store.locked():pass
        with patch.object(b.subprocess,'Popen',side_effect=AssertionError('must not launch')):
            with self.assertRaisesRegex(b.Refusal,'closure'):b.runtime(self.store,'check',[])

    def test_host_check_build_refused_before_child_launch(self):
        with patch.object(b,'Store',return_value=self.store),patch.object(b,'run_owned',side_effect=AssertionError('must not launch')),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(b.main(['host-check','--','--build-dir','private-build']),2)
        self.assertIn('private vendor output',output.getvalue())
    def test_host_check_unclosed_marker_refused_before_launch(self):
        with self.store.locked():b.save(self.store.path/'runtime-unclosed.json',{'closure_verified':False})
        with patch.object(b,'Store',return_value=self.store),patch.object(b,'run_owned',side_effect=AssertionError('must not launch')),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(b.main(['host-check']),2)

    def test_zip_symlink_metadata_bounded_before_read(self):
        f=self.root/'links.zip';m=zipfile.ZipInfo('link');m.create_system=3;m.external_attr=(stat.S_IFLNK|0o600)<<16
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr(m,b'x'*(b.MAX_PATH_BYTES+1))
        with patch.object(zipfile.ZipFile,'open',side_effect=AssertionError('must not read target')):
            with self.assertRaisesRegex(b.Refusal,'metadata bound'):
                with b.archive_entries(f):pass
    def test_tar_extended_metadata_bounded_before_read(self):
        with tarfile.open(self.archive,'w:bz2',format=tarfile.PAX_FORMAT) as t:
            m=tarfile.TarInfo('file');m.pax_headers={'comment':'x'*70000};m.size=1;t.addfile(m,io.BytesIO(b'x'))
        with self.assertRaisesRegex(b.Refusal,'metadata bound'):
            with b.archive_entries(self.archive):pass

if __name__=='__main__':unittest.main()
