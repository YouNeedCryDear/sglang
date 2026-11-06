"""Replay two malformed headers through SGLang without model inference.

Run with a normal SGLang environment and PYTHONPATH pointing to the source
checkout to compare. The old Harmony package needs its vocabulary cached.
"""

import json

from sglang.srt.entrypoints.context import HarmonyContext
from sglang.srt.entrypoints.harmony_utils import get_encoding, parse_output_message

cases = {
    "metadata_spliced": (
        "<|channel|>commentary to=functions.echo "
        "<|constrain|>commentary to=assistant "
        "<|constrain|>analysis to=functions.echo json"
        '<|message|>{"x":1}<|call|>'
    ),
    "missing_separator": '<|channel|>analysis to=functions.echo{"x":1}<|call|>',
}
encoding = get_encoding()
for name, text in cases.items():
    context = HarmonyContext([], {})
    tokens = encoding.encode(text, allowed_special="all")
    try:
        context.append_output(
            {
                "output_ids": tokens,
                "meta_info": {
                    "completion_tokens": len(tokens),
                    "finish_reason": {"type": "stop"},
                },
            }
        )
        items = [
            {
                "type": item.type,
                "name": getattr(item, "name", None),
                "arguments": getattr(item, "arguments", None),
            }
            for message in context.messages
            for item in parse_output_message(message)
        ]
        print(json.dumps({"case": name, "output": items}))
    except Exception as exc:
        print(json.dumps({"case": name, "error": type(exc).__name__, "message": str(exc)}))
