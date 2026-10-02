"""No hardware: test entry-point prior-closure admission using dependency doubles."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

source_root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(source_root/'tools'))
spec = importlib.util.spec_from_file_location('reviewed_lifecycle', source_root/'tools/forgix_usb_ram_trial.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
binding={'uid_sha256':'a'*64}
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    (root/'backups').mkdir()
    prior=root/'backups/prior.json'
    prior.write_text(json.dumps({'binding':binding,'status':'failed','collector_group_closed':False,'hardware_process_closed':False,'owned_hardware_closed':False}))
    prior.chmod(0o600)
    argv=['review','--action','recover','--factory-port','/synthetic-only','--private-dir',str(root/'backups/recovery'),
          '--prior-session',str(prior),'--binding','/synthetic-binding','--baseline-a','/synthetic-a','--baseline-b','/synthetic-b']
    with patch.object(m,'ROOT',root), patch.object(m,'original_binding',return_value=binding), \
         patch.object(m,'image_check',return_value={'picotool_executable':'synthetic','image_id':'synthetic'}), \
         patch.object(m,'freeze_inputs',return_value={}), patch.object(m.subprocess,'run',return_value=SimpleNamespace(returncode=0)), \
         patch.object(m.shutil,'which',return_value='synthetic'), patch.object(sys,'argv',argv), \
         patch.object(m,'full_preservation',return_value=({},None)) as full, redirect_stdout(io.StringIO()):
        code=m.main()
        print_result={'hardware_opened':False,'exit_code':code,'full_preservation_calls_with_unknown_prior_closure':full.call_count}
    print(json.dumps(print_result))
    assert code != 0 and full.call_count == 0, 'Unknown prior closure admitted device verification'
