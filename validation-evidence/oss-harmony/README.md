# SGLang oss-harmony migration evidence

Run on November 3, 2026. The candidate is `3d1442e6e85f77dc083d1111c3aa07a7ee17429d`, based on `a4bef204c51e1c1b7ed59593b85993a940367591`.

| Check | Before: openai-harmony 0.0.4 | After: oss-harmony 0.0.12 + compatibility adapter |
| --- | --- | --- |
| Responses unit suites | 106 tests, 81 subtests passed | 108 tests, 85 subtests passed |
| GPU API matrix | 12/12 passed | 12/12 passed |
| GPU final output comparison | Reference | 12/12 identical text and normalized results |
| Prompt render fixtures | Reference | 11/11 identical token arrays and decoded text |
| Full/incremental parser fixtures | Reference | 22/22 matching parsed-message results |
| Fresh cache, socket syscalls blocked | HarmonyError | Encode/decode succeeds; cache stays empty |

## GPU execution

[GPU_README.md](gpu/GPU_README.md) records the exact model revision, image digest, runtime versions, source overlay, server command, test commands, and comparison rules. One initially idle H200 NVL was used on an existing Colossus lease and freed afterward. No lease was changed.

The test image was `lmsysorg/sglang:v0.5.22-cu130` with **the tested source snapshots** supplied through `PYTHONPATH`; installed distribution metadata reporting 0.5.22 does not identify the Python implementation tested. Identical dependencies were used in both phases. This was not a fresh install of every dependency declared by current main.

The 12 cases exercise Responses text generation, function calls, explicit tool-result replay, and a Chat Completions control, each in streaming and non-streaming mode. [comparison.json](gpu/comparison.json) compares identical requests and final results. Raw requests, JSON responses, and SSE events are in [baseline](gpu/baseline) and [candidate](gpu/candidate). Generated identifiers, timestamps, and cache-hit counts are excluded from comparison. Network chunk boundaries and per-event IDs are not asserted identical.

Full test output: [baseline](gpu/baseline_unit.log), [candidate](gpu/candidate_unit.log). The candidate adds two regression tests with four header/body subcases.

## Library and rendering probes

The library probes used separate CPython 3.12.14 virtual environments with `openai-harmony==0.0.4` or `oss-harmony==0.0.12`, both with `pydantic==2.14.2` and `openai==2.8.0`.

A dependency-only switch changes four of 11 prompt fixtures: function-call recipient ordering and explicit JSON/code constraints in function, Python, and browser tool histories. The compatibility adapter restores the old token sequences. This follows the approach in [vLLM PR #55128](https://github.com/vllm-project/vllm/pull/55128).

- [before.json](library/before.json) and [after.json](library/after.json): direct-library rendering, including the four differences.
- [before-sglang.json](library/before-sglang.json) and [after-sglang.json](library/after-sglang.json): all 11 rendered token arrays/text match after applying the actual SGLang wrapper.
- [parse-before.json](library/parse-before.json) and [parse-after.json](library/parse-after.json): full and incremental parsing of the same baseline histories; 22 matching results.
- [offline-before.log](library/offline-before.log) and [offline-after.log](library/offline-after.log): empty-cache load under Linux seccomp denying socket creation, including native Rust networking.
- [proxy-before.json](library/proxy-before.json) and [proxy-after.json](library/proxy-after.json): independent verification of the reserved, unlistening loopback proxy used by the durable CI test.

`sglang_render_probe.py` and `body_probe.py` execute the actual source functions/test method via AST extraction to avoid importing GPU dependencies in the small local environments. The complete SGLang tests and GPU run above provide integration coverage; these isolated probes alone are not presented as full-runtime tests. The copied probe scripts only change file lookup to paths relative to this checkout.

To reproduce the local probes, create separate environments and run from the evidence directory:

```bash
uv venv /tmp/harmony-before
uv venv /tmp/harmony-after
uv pip install --python /tmp/harmony-before/bin/python 'openai-harmony==0.0.4' 'openai==2.8.0' 'pydantic==2.14.2'
uv pip install --python /tmp/harmony-after/bin/python 'oss-harmony==0.0.12' 'openai==2.8.0' 'pydantic==2.14.2'

# Warm the original library's cache online for rendering/parsing comparisons.
/tmp/harmony-before/bin/python library/render_probe.py
/tmp/harmony-before/bin/python library/sglang_render_probe.py
/tmp/harmony-after/bin/python library/sglang_render_probe.py
/tmp/harmony-before/bin/python library/parse_probe.py
/tmp/harmony-after/bin/python library/parse_probe.py
/tmp/harmony-before/bin/python library/body_probe.py
/tmp/harmony-after/bin/python library/body_probe.py
# This intentionally fails, reproducing the header regression without the adapter:
/tmp/harmony-after/bin/python library/body_probe.py --unadapted

# Linux with libseccomp.so.2; old fails, new succeeds without a cached vocabulary.
/tmp/harmony-before/bin/python library/offline_probe.py
/tmp/harmony-after/bin/python library/offline_probe.py
```

## Other checks and limits

- [benchmark_headers.py](benchmark_headers.py) measures final header-normalization overhead on 1, 10, 100, and 1,000 tool messages; [results](header_normalization_performance.json). Histories with no assistant tool recipients bypass normalization. This is CPU helper timing, not model-serving throughput.
- All changed-file pre-commit hooks passed: [log](precommit.log).
- All six Python manifests contain only `oss-harmony==0.0.12` as their Harmony distribution dependency.
- `uv pip install --dry-run --excludes harmony-excludes.txt gpt-oss` resolved 44 packages without adding `openai-harmony`; the exclusion file contains `openai-harmony`. This checks the documented optional demo-tool install path.
- Mintlify validation was unavailable locally because `mint` and `npx` were absent.
- This is a functional parity validation on GPT-OSS 20B and one NVIDIA GPU. It does not claim exhaustive model accuracy, other-accelerator execution, or a throughput improvement.
- Rust model-gateway packaging is outside this Python-runtime migration.
