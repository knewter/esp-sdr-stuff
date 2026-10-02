"""No hardware: exercise failed group cleanup plus failed marker persistence."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

root=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(root/'tools'))
spec=importlib.util.spec_from_file_location('reviewed_lifecycle',root/'tools/forgix_usb_ram_trial.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
results=[]
for cleanup in (m.OwnedHardwareClosureError('synthetic unclosed group'),OSError('synthetic killpg failure')):
    with tempfile.TemporaryDirectory() as tmp:
        proc=Mock();proc.pid=123;proc.wait.return_value=0
        with patch.object(m.subprocess,'Popen',return_value=proc),patch.object(m,'stop_process',side_effect=cleanup), \
             patch.object(m,'mark_unclosed',side_effect=OSError('synthetic storage failure')):
            try:
                m.owned_worker(['synthetic-only'],Path(tmp)/'log',9,1)
            except BaseException as exc:
                results.append({'cleanup_type':type(cleanup).__name__,'surfaced_type':type(exc).__name__,
                                'closure_exception_preserved':isinstance(exc,m.OwnedHardwareClosureError)})
print(json.dumps({'hardware_opened':False,'cases':results}))
assert all(row['closure_exception_preserved'] for row in results), 'Unknown cleanup was masked by persistence failure'
