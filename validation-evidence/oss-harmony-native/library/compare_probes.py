"""Compare saved tokens/text and both parser modes; assert the expected deltas."""

import json
from pathlib import Path

root = Path(__file__).resolve().parent


def read(name):
    return json.loads((root / name).read_text())


before = read("before.json")
after = read("after.json")
sglang = read("after-sglang.json")
rows = []
for name in before:
    old, native = before[name], after[name]
    row = {
        "case": name,
        "same_as_openai_harmony_0_0_4": old == native,
        "same_as_native_oss_harmony_0_0_12": sglang[name] == native,
    }
    if old != native:
        for key, value in (("old", old), ("native", native)):
            row[f"{key}_assistant_header"] = value["text"].split(
                "<|start|>assistant"
            )[1].split("<|message|>")[0]
    rows.append(row)
result = {
    "cases": rows,
    "old_render_equal": sum(x["same_as_openai_harmony_0_0_4"] for x in rows),
    "native_render_equal": sum(x["same_as_native_oss_harmony_0_0_12"] for x in rows),
    "old_token_parsing_equal": read("before-parse.json") == read("after-parse.json"),
    "native_parsing_full_equals_stream": all(
        case["full"] == case["stream"] for case in read("after-native-parse.json").values()
    ),
}
assert result["old_render_equal"] == 7
assert result["native_render_equal"] == 11
assert result["old_token_parsing_equal"]
assert result["native_parsing_full_equals_stream"]
assert {row["case"] for row in rows if not row["same_as_openai_harmony_0_0_4"]} == {
    "tool_call", "tool_call_json", "python_code", "browser_json"
}
(root / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
