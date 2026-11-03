import ast, json, types, sys, unittest
from pathlib import Path
import openai_harmony
source_path=Path(__file__).resolve().parents[3] / 'python/sglang/srt/entrypoints/harmony_utils.py'
tree=ast.parse(source_path.read_text())
names={'get_encoding','render_for_completion','_use_legacy_tool_call_headers'}
functions=ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names],type_ignores=[])
namespace={name:getattr(openai_harmony,name) for name in dir(openai_harmony)}
namespace['_harmony_encoding']=None
exec(compile(functions,str(source_path),'exec'),namespace)
if '--unadapted' in sys.argv:
 namespace['_use_legacy_tool_call_headers']=lambda tokens:tokens
module=types.ModuleType('sglang.srt.entrypoints.harmony_utils')
module.__dict__.update(namespace)
sys.modules['sglang.srt.entrypoints.harmony_utils']=module
test_path=Path(__file__).resolve().parents[3] / 'test/registered/unit/entrypoints/openai/test_serving_responses.py'
test_tree=ast.parse(test_path.read_text())
cls=next(node for node in test_tree.body if isinstance(node,ast.ClassDef) and node.name=='HarmonyResponsesTestCase')
method=next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=='test_harmony_tool_replay_preserves_legacy_header_and_body')
exec(compile(ast.Module(body=[method],type_ignores=[]),str(test_path),'exec'),namespace)
namespace[method.name](unittest.TestCase())
print('PASS: all four actual golden-header/body regression subcases')
