# GPU before/after validation

Run date: November 3, 2026 (America/Los_Angeles).

- Baseline source: `a4bef204c51e1c1b7ed59593b85993a940367591`, `openai-harmony==0.0.4`.
- Candidate: `3d1442e6e85f77dc083d1111c3aa07a7ee17429d`, `oss-harmony==0.0.12` and its Harmony rendering compatibility helper.
- Hardware: one NVIDIA H200 NVL (143771 MiB), driver 615.71.10. Selected GPU was idle before validation and returned to 0 MiB afterward.
- Model: `openai/gpt-oss-20b`, revision `6cee5e81ee83917806bbde320786a8fb61efebee` (MXFP4).
- Runtime image: `lmsysorg/sglang:v0.5.22-cu130`, digest `sha256:e3a4f06001a29542fc4a8638536d9ffc5eb9c9942b08603c09b19a56eae4a1ae`.
- Python source was loaded from the source snapshot with `PYTHONPATH=/work/source/python`; the image's installed distribution metadata still reports SGLang 0.5.22. Both phases used the current source, rather than the installed image's Python implementation.
- Both phases used Python 3.12.15, Torch 2.14.1+cu130, transformers 5.19.0, triton 3.8.0, flashinfer-python 0.7.1, sglang-kernel 0.4.9, openai 2.8.0, and tml-renderers 0.1.0. See `shared_runtime_versions.json` and each phase's `versions.json`.

The baseline source archive was extracted once. After baseline completion the isolated container was restarted, only the candidate's changed Python runtime/test files were overlaid, `openai-harmony` was uninstalled, and `oss-harmony==0.0.12` was installed with `--no-deps`. The rest of the runtime stayed unchanged. The overlaid files matched the candidate commit SHA256 values:

```
9d871d577bac3aa572bd8ec79186825a05f460db1e1da1d2fb14ecf8fdda0a21  python/sglang/srt/entrypoints/harmony_utils.py
0cb5b9ff810fde6e42e99f42c1e6eb9463d37c41c5dc9eae409a3d6de354a382  test/registered/unit/entrypoints/openai/test_serving_responses.py
```

## Results

| Check | Baseline | Candidate |
| --- | --- | --- |
| Existing Responses unit suites | 106 passed, 81 subtests passed | 108 passed, 85 subtests passed (includes new regression tests) |
| GPU API cases | 12/12 passed, all HTTP 200 | 12/12 passed, all HTTP 200 |
| Per-case request equality | 12/12 | 12/12 |
| Per-case output text equality | 12/12 | 12/12 |
| Per-case canonical result equality | 12/12 | 12/12 |

The 12 cases cover three plain Responses prompts, tool calling, tool-result replay, and a Chat Completions control, each with streaming and non-streaming. Tool calls returned `get_weather` with `{"city":"Paris"}`. Tool-result replay correctly used the supplied `21 C` / `sunny` result. `comparison.json` contains the case-by-case comparison.

Canonical comparison removes generated identifiers, timestamps, and cache-hit counters. For Responses it compares the final structured response, including generated text, reasoning, tool arguments, completion status, and remaining usage fields. For Chat streaming it compares assembled answer and reasoning text. Complete original JSON/SSE events are retained in the per-case files; event IDs and network chunk boundaries are not claimed identical.

## Reproduction commands

Use the same image and an isolated container with one GPU, `--ipc=host`, and the source/evidence directory mounted as `/work`. Install `openai==2.8.0 tml-renderers==0.1.0 pytest-asyncio==1.4.1.post1` for both phases. Set `HF_HOME=/work/model-cache`. Resolve the model at the pinned revision above. Set `PYTHONPATH=/work/source/python` and `SGLANG_RUST_BUILD_MODE=auto` (the source TreeCore extension was built from the checked-out Rust sources).

Server command, identical in both phases:

```bash
python -m sglang.launch_server \
  --model-path "$model_path" \
  --served-model-name gpt-oss-20b \
  --host 0.0.0.0 --port 30071 \
  --tp-size 1 --mem-fraction-static 0.70 \
  --context-length 8192 --max-running-requests 8 \
  --reasoning-parser gpt-oss --tool-call-parser gpt-oss \
  --random-seed 42 --disable-cuda-graph
```

Requests use `temperature=0`, `reasoning.effort=low`, and a 512-token output cap. The same fixed request order is in `validate_serving.py`.

```bash
HARMONY_EVIDENCE=/path/to/validation-evidence/oss-harmony
cd /work/source
python -m pytest -q \
  test/registered/unit/entrypoints/openai/test_serving_responses.py \
  test/registered/unit/entrypoints/openai/test_serving_responses_stream.py
python "$HARMONY_EVIDENCE/gpu/validate_serving.py" baseline --output-dir /work/results
# Stop the baseline server, switch to the candidate source, then:
python -m pip uninstall -y openai-harmony
python -m pip install --no-deps oss-harmony==0.0.12
# Restart using the same server command and run the same tests.
python "$HARMONY_EVIDENCE/gpu/validate_serving.py" candidate --output-dir /work/results
python "$HARMONY_EVIDENCE/gpu/compare_serving.py" /work/results
```

This is a functional parity check, not a throughput benchmark. Both servers were stopped after testing; the prior task's container and GPU allocation were left intact.
