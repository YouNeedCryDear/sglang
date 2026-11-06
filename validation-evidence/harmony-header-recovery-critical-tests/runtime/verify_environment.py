import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import py_compile
import torch

work = Path('/work/critical-tests-20261105')
checks = {}
for name, manifest_name in [('source', 'tested_source_sha256.json'), ('source_upstream', 'upstream_with_final_tests_sha256.json')]:
    hashes = json.loads((work / manifest_name).read_text())
    for path, expected in hashes.items():
        actual = work / name / path
        assert hashlib.sha256(actual.read_bytes()).hexdigest() == expected, str(actual)
        py_compile.compile(str(actual), doraise=True)
    assert not (work / name / 'python/sglang/srt/entrypoints/harmony_recovery.py').exists()
    checks[name] = {'sha256_verified': hashes, 'compiled_files': len(hashes), 'wrapper_absent': True}
names = ['sglang', 'torch', 'openai-harmony', 'oss-harmony', 'openai', 'transformers', 'sglang-kernel', 'tml-renderers', 'pytest', 'pytest-asyncio']
versions = {name: metadata.version(name) if next(metadata.distributions(name=name), None) else None for name in names}
versions.update(python=platform.python_version(), architecture=platform.machine(), cuda_available=torch.cuda.is_available(), cuda_device_count=torch.cuda.device_count())
print(json.dumps({'source_manifest': json.loads((work/'source_manifest.json').read_text()), 'verification': checks, 'environment': versions}, indent=2))
