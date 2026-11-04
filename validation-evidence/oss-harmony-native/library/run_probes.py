"""Run with HARMONY_BEFORE_PYTHON / HARMONY_AFTER_PYTHON pointing at isolated venvs."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
source_root = Path(os.environ.get("SGLANG_SOURCE_ROOT", root.parents[2]))
interpreters = {
    version: os.environ[f"HARMONY_{version.upper()}_PYTHON"]
    for version in ("before", "after")
}
runs = {}
metadata = {}


def run(version, script, suffix, args=()):
    result = subprocess.run(
        [interpreters[version], str(root / script), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    name = f"{version}{suffix}"
    is_json = suffix in ("", "-sglang", "-parse", "-native-parse", "-proxy")
    (root / f"{name}.{'json' if is_json else 'log'}").write_text(result.stdout)
    stderr_path = root / f"{name}.stderr.log"
    if result.stderr:
        stderr_path.write_text(result.stderr)
    elif stderr_path.exists():
        stderr_path.unlink()
    runs[name] = result.returncode


for version in ("before", "after"):
    for script, suffix in (
        ("render_probe.py", ""),
        ("sglang_render_probe.py", "-sglang"),
        ("parse_probe.py", "-parse"),
        ("native_body_probe.py", "-body"),
        ("offline_probe.py", "-offline"),
        ("proxy_probe.py", "-proxy"),
    ):
        run(version, script, suffix)
    metadata[version] = json.loads(subprocess.check_output(
        [interpreters[version], "-c", "import importlib.metadata as m,json,platform; "
         "print(json.dumps({'python': platform.python_version(), 'packages': "
         "{d.metadata['Name']:d.version for d in m.distributions()}}))"],
        text=True,
    ))

run("after", "native_body_probe.py", "-body-legacy-shim", ("--legacy-shim",))
run("after", "parse_probe.py", "-native-parse", ("after.json",))
metadata["source"] = {
    "commit": subprocess.check_output(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True
    ).strip(),
    "sha256": {
        path: hashlib.sha256((source_root / path).read_bytes()).hexdigest()
        for path in (
            "python/sglang/srt/entrypoints/harmony_utils.py",
            "test/registered/unit/entrypoints/openai/test_serving_responses.py",
        )
    },
}
(root / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
(root / "probe_exit_codes.json").write_text(json.dumps(runs, indent=2) + "\n")
print(json.dumps(runs, indent=2))
expected_failures = {"before-body", "before-offline", "after-body-legacy-shim"}
assert all(code == (1 if name in expected_failures else 0) for name, code in runs.items())
assert json.loads((root / "before-proxy.json").read_text())["returncode"] == 1
assert json.loads((root / "after-proxy.json").read_text())["returncode"] == 0
subprocess.run([sys.executable, str(root / "compare_probes.py")], check=True)
