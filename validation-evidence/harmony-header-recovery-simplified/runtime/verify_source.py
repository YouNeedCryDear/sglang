import hashlib
import json
from pathlib import Path
import py_compile

root = Path('/work/source_fixed')
hashes = json.loads(Path('/work/tested_source_sha256.json').read_text())
assert len(hashes) == 5
for name, expected in hashes.items():
    path = root / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
    py_compile.compile(str(path), doraise=True)
removed = root / 'python/sglang/srt/entrypoints/harmony_recovery.py'
assert not removed.exists()
print(json.dumps({'source_commit': 'ae3fffc9d0ab0bbb7f311a02941f262ca62efea0', 'sha256_verified_files': hashes, 'compiled_files': 5, 'harmony_recovery_wrapper_absent': True}, indent=2))
