"""No hardware: execution input changes while offline preflight waits for lock."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

source_root=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(source_root/'tools'))
spec=importlib.util.spec_from_file_location('reviewed_lifecycle',source_root/'tools/forgix_usb_ram_trial.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'backups').mkdir()
    fixture=root/'fixture.py';fixture.write_bytes(b'initial execution source')
    frozen={'source_commit':'synthetic','inputs':{'fixture.py':hashlib.sha256(fixture.read_bytes()).hexdigest()}}
    def previous_owner_finishes(*args):fixture.write_bytes(b'changed execution source')
    argv=['review','--action','run','--private-dir',str(root/'backups/session'),'--binding','/synthetic-binding',
          '--baseline-a','/synthetic-a','--baseline-b','/synthetic-b','--artifact','/synthetic-artifact']
    with patch.object(m,'ROOT',root),patch.object(m,'original_binding',return_value={}), \
         patch.object(m,'artifact_check',return_value={}),patch.object(m,'image_check',return_value={}), \
         patch.object(m,'freeze_inputs',return_value=frozen), \
         patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)), \
         patch.object(m.shutil,'which',return_value='synthetic'),patch.object(sys,'argv',argv), \
         patch.object(m.fcntl,'flock',side_effect=previous_owner_finishes),patch.object(m,'run_session') as session, \
         redirect_stdout(io.StringIO()):
        code=m.main()
    print(json.dumps({'hardware_opened':False,'exit_code':code,'run_session_calls_after_input_mutation':session.call_count}))
    assert code != 0 and session.call_count == 0, 'Post-lock changed source admitted hardware session'
