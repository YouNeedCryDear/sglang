"""Measure only the compatibility adapter; no GPU dependencies required."""

import ast
import importlib.metadata
import json
import platform
import timeit
from pathlib import Path

import openai_harmony
from openai_harmony import Conversation, HarmonyEncodingName, Message, Role

source = Path(__file__).resolve().parents[2] / "python/sglang/srt/entrypoints/harmony_utils.py"
names = {"get_encoding", "_use_legacy_tool_call_headers"}
module = ast.Module(
    body=[node for node in ast.parse(source.read_text()).body
          if isinstance(node, ast.FunctionDef) and node.name in names],
    type_ignores=[],
)
encoding = openai_harmony.load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
namespace = {name: getattr(openai_harmony, name) for name in dir(openai_harmony)}
namespace["_harmony_encoding"] = encoding
exec(compile(module, str(source), "exec"), namespace)
normalize = namespace["_use_legacy_tool_call_headers"]
results = []
for count in (1, 10, 100, 1000):
    message = (
        Message.from_role_and_content(Role.ASSISTANT, '{"text":"' + "result " * 100 + '"}')
        .with_channel("commentary")
        .with_recipient("functions.echo")
        .with_content_type("json")
    )
    conversation = Conversation.from_messages([message] * count)
    tokens = encoding.render_conversation_for_completion(conversation, Role.ASSISTANT)
    normalize(tokens)
    repeats = 3 if count == 1000 else 10
    results.append({
        "tool_calls": count,
        "tokens": len(tokens),
        "repeats": repeats,
        "normalization_mean_ms": 1000 * timeit.timeit(lambda: normalize(tokens), number=repeats) / repeats,
    })
print(json.dumps({
    "scope": "CPU compatibility adapter only; not a throughput benchmark",
    "python": platform.python_version(),
    "machine": platform.machine(),
    "oss-harmony": importlib.metadata.version("oss-harmony"),
    "measurements": results,
}, indent=2))
