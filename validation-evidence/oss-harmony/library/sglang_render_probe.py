import ast
import json
from pathlib import Path
import openai_harmony

# Execute the actual rendering functions without importing unrelated GPU utilities.
source_path=Path(__file__).resolve().parents[3] / 'python/sglang/srt/entrypoints/harmony_utils.py'
tree=ast.parse(source_path.read_text())
names={'get_encoding','render_for_completion','_use_legacy_tool_call_headers'}
functions=ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names],type_ignores=[])
namespace={name:getattr(openai_harmony,name) for name in dir(openai_harmony)}
namespace['_harmony_encoding']=None
exec(compile(functions,str(source_path),'exec'),namespace)
probe=Path(__file__).with_name('render_probe.py').read_text()
probe=probe.replace('tokens=enc.render_conversation_for_completion(Conversation.from_messages(msgs),Role.ASSISTANT)','tokens=render_for_completion(msgs)')
namespace['render_for_completion']=namespace['render_for_completion']
exec(compile(probe,'render_probe.py','exec'),namespace)
