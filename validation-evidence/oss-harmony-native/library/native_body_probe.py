"""Run the actual test method with real library bindings and extracted SGLang functions.

This isolated probe avoids unrelated server/GPU imports; the whole test file is
also exercised separately in the serving environment. --legacy-shim uses the
pre-removal production source to demonstrate the regression assertion.
"""
import ast
import json
import os
import sys
import types
import unittest
from pathlib import Path
import openai_harmony

root = Path(__file__).parent
worktree = Path(os.environ.get('SGLANG_SOURCE_ROOT', Path(__file__).resolve().parents[3]))
source_path = worktree / 'python/sglang/srt/entrypoints/harmony_utils.py'
if '--legacy-shim' in sys.argv:
    source_path = root / 'harmony_utils_with_legacy_shim.py'
names = {'get_encoding', 'render_for_completion', '_use_legacy_tool_call_headers'}
functions = ast.Module(body=[node for node in ast.parse(source_path.read_text()).body
                            if isinstance(node, ast.FunctionDef) and node.name in names],
                       type_ignores=[])
namespace = {name: getattr(openai_harmony, name) for name in dir(openai_harmony)}
namespace['_harmony_encoding'] = None
exec(compile(functions, str(source_path), 'exec'), namespace)
module = types.ModuleType('sglang.srt.entrypoints.harmony_utils')
module.__dict__.update(namespace)
sys.modules['sglang.srt.entrypoints.harmony_utils'] = module
test_path = worktree / 'test/registered/unit/entrypoints/openai/test_serving_responses.py'
cls = next(node for node in ast.parse(test_path.read_text()).body
           if isinstance(node, ast.ClassDef) and node.name == 'HarmonyResponsesTestCase')
method = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
              and node.name == 'test_harmony_tool_replay_preserves_native_header_and_body')
exec(compile(ast.Module(body=[method], type_ignores=[]), str(test_path), 'exec'), namespace)
case = type('ActualNativeHeaderRegression', (unittest.TestCase,), {method.name: namespace[method.name]})
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(case))
print(json.dumps({'source': str(source_path), 'successful': result.wasSuccessful(),
                  'failures': [str(test) for test, _ in result.failures],
                  'errors': [str(test) for test, _ in result.errors]}))
sys.exit(0 if result.wasSuccessful() else 1)
