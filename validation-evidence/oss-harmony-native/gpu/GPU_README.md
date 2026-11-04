# Native oss-harmony GPU validation

Both package versions passed all 16 functional API cases on one NVIDIA GB300. All 32 requests returned HTTP 200. The 16 request bodies were identical across runs; final answer text matched in 14/16 cases and normalized complete responses matched in 10/16. Native tool-history rendering deliberately changes prompts, so this is evidence of API and semantic compatibility, not bitwise generation equivalence.

## Source, model, and runtime

- Baseline: SGLang `a4bef204c51e1c1b7ed59593b85993a940367591`, `openai-harmony==0.0.4`.
- Candidate: SGLang `afbe4d556217b6cc9668aeea1ec58fec1d592020`, `oss-harmony==0.0.12`, native rendering without the legacy helper.
- The full baseline git archive was loaded through `PYTHONPATH=/work/source/python`. Candidate runtime Python source is identical to baseline; the candidate unit-test file was overlaid and the Harmony distribution replaced. Package manifests and documentation do not affect this runtime overlay. This is a controlled source-overlay validation, not a complete clean installation of each SGLang package.
- Final remote `harmony_utils.py` SHA256: `f6908a8aa8e7563e1009ff374c423d75dc16479a3e3aab91ea157bc39e120afb` (also identical to baseline).
- Final remote `test_serving_responses.py` SHA256: `bc4090aeb2d35e2980efeb89bcc201b5534e8c48a4dcbef4962ea1d9e6a55786`.
- Model: `openai/gpt-oss-20b`, revision `6cee5e81ee83917806bbde320786a8fb61efebee`, MXFP4 weights. See `model_revision.json` and `download_model.py`.
- Image: `lmsysorg/sglang:v0.5.23-cu130`, digest `sha256:f832b5c39559c9caa900b22ad37c76fcce66470676855c42052102c537812f1f`.
- Hardware: 1 NVIDIA GB300, 256703 MiB, aarch64, driver `610.43.02`. The GPU was idle before launch; after stopping the validation container it returned to 1 MiB, 0% utilization, and no compute processes.
- Shared runtime: Python `3.12.16`, torch `2.14.1+cu130`, transformers `5.19.0`, triton `3.8.0`, flashinfer-python `0.7.2`, sglang-kernel `0.4.10`, openai `2.8.0`, tml-renderers `0.1.0`, pytest `9.2.0`, pytest-asyncio `1.4.1.post1`.
- Per-phase `versions.json` files record actual installed distributions. Their `sglang: 0.5.23` field describes image distribution metadata; the executed source is the overlay above.

## Results

| Check | Baseline | Candidate |
| --- | --- | --- |
| GPU API smoke cases | 16/16 passed | 16/16 passed |
| Unit tests in the two Responses suites | 106 passed, 81 subtests passed | 108 passed, 85 subtests passed |

The matrix includes Responses arithmetic, capital, literal output, initial tool call, tool-result replay, multi-turn next-tool call and replay, plus Chat Completions controls. Every scenario runs both streaming and non-streaming. Multi-turn requests replay complete Paris and London tool turns, then request Rome weather or replay the Rome result. All requests use temperature 0, a 512-token output limit, and low reasoning effort.

`tool_replay` and `tool_replay_stream` change wording but both correctly answer with 21 degrees and sunny conditions. The multi-turn next-call cases retain exactly `get_weather({"city":"Rome"})`; the multi-turn replay answers retain Rome, 25 degrees and clear conditions. These six history cases change reasoning and/or output-token usage. The remaining 10 cases match normalized complete responses exactly. `comparison.json` records all equality results and differing JSON paths; raw per-case request, JSON response or parsed SSE events, semantic assertions, and normalized response are under `baseline/` and `candidate/`.

Normalization removes only IDs, call IDs, timestamps, system fingerprint, request ID and cached-token counters recursively. Responses comparison retains output items (including model-generated reasoning), arguments, status and other usage fields. Chat streaming comparison assembles text and reasoning. Raw event boundaries and generated identifiers are not asserted equal. The 14/16 text count includes empty final text for tool-call cases; those cases separately assert one correctly named call and exact JSON arguments.

## Commands and setup

Only this experiment's isolated container was used. No lease changes were made; artifacts and model cache were retained after shutdown. The published evidence omits private host and lease identifiers and raw server-info metadata.

Container setup used:

```sh
docker run -d --name oss-harmony-native-validation-20261103 \
  --gpus device=0 --ipc=host \
  -v /tmp/oss-harmony-native-evidence:/work -w /work \
  -e HF_HOME=/work/model-cache \
  lmsysorg/sglang:v0.5.23-cu130 sleep infinity
```

The image already contained `openai-harmony==0.0.4`. Common dependencies required by the current source/tests were installed inside the task container before either phase:

```sh
python -m pip install openai==2.8.0 tml-renderers==0.1.0 pytest-asyncio==1.4.1.post1
python /work/download_model.py
```

The initial baseline vocabulary loader failed with `failed to download or load vocab file`. We then fetched the official `https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken` using Python requests and placed it in the standard `/tmp/tiktoken-rs-cache/<SHA1(url)>` cache. It returned HTTP 200, 3613922 bytes, SHA256 `446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`. The baseline loader, tests and server then succeeded. The specific cause of the original downloader failure was not established; this GPU run was not an offline-network experiment.

Both phases ran the same server command, with `model_path.txt` pointing to the same fixed snapshot:

```sh
export PYTHONPATH=/work/source/python
export SGLANG_RUST_BUILD_MODE=auto
model_path=$(cat /work/model_path.txt)
python -m sglang.launch_server \
  --model-path "$model_path" --served-model-name gpt-oss-20b \
  --host 0.0.0.0 --port 30071 \
  --tp-size 1 --mem-fraction-static 0.70 \
  --context-length 8192 --max-running-requests 8 \
  --reasoning-parser gpt-oss --tool-call-parser gpt-oss \
  --random-seed 42 --disable-cuda-graph
```

The image resolved GB300 defaults to FlashInfer MXFP4 MoE and TRTLLM attention. Source TreeCore was compiled via the automatic build mode. Initial baseline kernel tuning populated a cache reused by candidate; timing is not compared.

Tests and clients ran inside the container:

```sh
cd /work/source
PYTHONPATH=/work/source/python python -m pytest -q \
  test/registered/unit/entrypoints/openai/test_serving_responses.py \
  test/registered/unit/entrypoints/openai/test_serving_responses_stream.py
PYTHONPATH=/work/source/python python /work/validate_serving.py baseline
```

After baseline completion the task container was restarted, the final candidate test file copied into the source tree, and Harmony replaced in this order to avoid shared-module uninstall conflicts:

```sh
python -m pip uninstall -y openai-harmony
python -m pip install --no-deps oss-harmony==0.0.12
```

The same unit-test and server commands were repeated, followed by:

```sh
PYTHONPATH=/work/source/python python /work/validate_serving.py candidate
python /work/compare_serving.py /work
```

`launch_baseline.sh` and `launch_candidate.sh` preserve the actual phase commands and logging paths. `baseline_unit.log` and `candidate_unit.log` contain the complete pytest output. This small functional matrix does not measure broad model accuracy, long-running reliability, throughput or latency, nor does it prove identical output for arbitrary histories.
