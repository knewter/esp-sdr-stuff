"""Bind this offline replay to the independently reviewed source bytes."""
import hashlib
import json
from pathlib import Path
import sys

root=Path(sys.argv[1]).resolve()
receipt=json.loads((Path(__file__).parent/'receipt.json').read_text())
for name,digest in receipt['reviewed_file_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest, 'Reviewed source changed: '+name
print(json.dumps({'hardware_opened':False,'reviewed_source_hashes_match':True,
                  'reviewed_author_commit':receipt['reviewed_author_commit']}))
