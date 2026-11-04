# Harmony malformed-header recovery: full-runtime CPU validation

The final recovery source passes both complete Responses unit suites with either Harmony distribution: **111 tests and 116 subtests passed** for `openai-harmony==0.0.4`, and the same counts for `oss-harmony==0.0.12`.

The same new regression tests run against unchanged upstream production source fail in **20 subcases across two test methods** with either distribution. These failures demonstrate the parser/output bugs, rather than test-fixture or constructor incompatibilities.

## Source and experiment

- Upstream source: `3f5b1bec8e00115bc8439b5b9a9da902822d2f82`.
- Fixed source: `75429de8959a18da1b316bc5947949ff1fae9184`.
- Fixed tree: full upstream git archive plus the final six changed source/test files. `tested_source_sha256.json` records every changed file; all six hashes were verified on the test host and against the final commit.
- Upstream regression tree: unchanged upstream production code plus only the final two test files. No production edits, parser replacements, or constructor adaptations were used.
- The `baseline/` directory denotes the **openai-harmony 0.0.4 environment**, and `candidate/` denotes **oss-harmony 0.0.12**. Both environments tested the same fixed source and the same upstream reproduction tree.
- These tests invoke the real `create_responses` handler and Harmony parser directly. Only tokenizer-manager generation is stubbed to supply deterministic malformed token streams. Streaming cases consume the real SSE generator. No network API server, model weights, model inference or GPU kernels were launched.

## Results

| Harmony distribution | Fixed full suites | Upstream targeted reproduction |
| --- | --- | --- |
| openai-harmony 0.0.4 | 111 tests + 116 subtests passed | 20 subcases failed as expected |
| oss-harmony 0.0.12 | 111 tests + 116 subtests passed | 20 subcases failed as expected |

Pytest reports the targeted run as `20 failed, 2 passed`: the failures are unittest subtests inside the two selected test methods. The two-method count should not be interpreted as successful regression behavior.

The targeted cases cover four headers: spliced channel/recipient/constrain metadata, a missing message separator, a missing separator after constrain, and a valid function recipient on the analysis channel. Each has one non-streaming case and four streaming cases (incremental versus cumulative engine tokens, with token-by-token versus whole-output chunks), giving 4 + 16 failing upstream subcases.

Observed upstream failures in both environments:

- Spliced metadata returns an HTTP 400 response in the non-streaming handler and raises `HarmonyError` in streaming: unexpected tokens remain in the message header.
- Missing-separator cases omit the function-call output item.
- The valid analysis-channel function recipient is emitted as reasoning instead of a function call.

The fixed full suites also check declared-tool/JSON guards, preservation of body text (including literal Harmony-looking text and Unicode), surrounding reasoning/message output, SSE item order/IDs, sequence numbers, argument deltas and completion events. See the committed tests and the complete logs for exact assertions and coverage.

## Runtime and isolation

Both environments used isolated containers on the same aarch64 host. Docker used `--runtime=runc -e NVIDIA_VISIBLE_DEVICES=void`, with no `--gpus` flag. Both recorded `torch.cuda.is_available() == false` and `torch.cuda.device_count() == 0`.

Base image: `lmsysorg/sglang:v0.5.23-cu130`, digest `sha256:f832b5c39559c9caa900b22ad37c76fcce66470676855c42052102c537812f1f`. The previously validated dependency layer was snapshotted locally as image ID `sha256:8633e6bab2b10aee55b0e06983f1df07d2f03d1ccd126ef9c555809e2648cb7c`; it is a local snapshot, not a published image. The layer had the same shared dependency updates used for the prior migration validation:

```sh
python -m pip install openai==2.8.0 tml-renderers==0.1.0 pytest-asyncio==1.4.1.post1
```

Actual shared versions: Python `3.12.16`, torch `2.14.1+cu130`, transformers `5.19.0`, sglang-kernel `0.4.10`, openai `2.8.0`, tml-renderers `0.1.0`, pytest `9.2.0`, pytest-asyncio `1.4.1.post1`. The per-environment `environment_ready.json` files record installed versions and successful Harmony encoding probes. Their SGLang `0.5.23` value is image distribution metadata; executed source came from `PYTHONPATH` overlays at the commits above.

The baseline container uninstalled oss-harmony before installing openai-harmony to avoid shared module-file conflicts:

```sh
python -m pip uninstall -y oss-harmony
python -m pip install --no-deps openai-harmony==0.0.4
```

The candidate container retained `oss-harmony==0.0.12` from the validated dependency snapshot. The baseline encoder used the existing standard vocabulary cache. This run makes no claim about fresh offline installation.

## Commands

Run inside each environment; full suite commands were identical:

```sh
cd /work/source_fixed
PYTHONPATH=/work/source_fixed/python python -m pytest -q \
  test/registered/unit/entrypoints/openai/test_serving_responses.py \
  test/registered/unit/entrypoints/openai/test_serving_responses_stream.py
```

The upstream reproduction used:

```sh
cd /work/source_upstream
PYTHONPATH=/work/source_upstream/python python -m pytest -q \
  test/registered/unit/entrypoints/openai/test_serving_responses.py::HarmonyHeaderRecoveryTestCase::test_malformed_headers_recover_function_call_response \
  test/registered/unit/entrypoints/openai/test_serving_responses_stream.py::HarmonyStreamLifecycleTestCase::test_repaired_headers_preserve_function_call_stream
```

`run_remote_tests.sh` preserves extraction, overlay, hash verification and exact Docker execution commands. Each environment directory includes full test logs, exit codes and version probes. `summary.json` provides machine-readable counts.

Both task containers were stopped after collection. No lease was changed. The host GPU remained unused by these tests and was verified afterward at 1 MiB, 0% utilization, with no compute processes. Cached artifacts were retained.

These deterministic handler tests establish the covered parser and SSE behavior. They do not measure natural malformed-header frequency, broad model accuracy, throughput, or latency.

## Minimal reproduction script

`reproduce.py` is the exact short script intended for the PR reproduction steps. It uses the real SGLang `HarmonyContext` and output parser with two fixed token streams, without model inference. The script was run against both source revisions in both package environments:

```sh
PYTHONPATH=/work/source_upstream/python python /work/reproduce.py
PYTHONPATH=/work/source_fixed/python python /work/reproduce.py
```

For either Harmony package, upstream reports `HarmonyError` for `metadata_spliced` and `output: []` for `missing_separator`. The fixed source reports one `function_call` named `echo`, with arguments `{"x":1}`, in both cases. The four `minimal_repro_{upstream,fixed}.jsonl` files under `baseline/` and `candidate/` capture these results. Their first record supplies the source commit, actual package/version, and CUDA-unavailable context; the next two records are the script's unmodified output. `run_repro_context.py` adds only that metadata record before executing the exact script, and `run_repro_remote.sh` preserves the invocation commands. Both containers were stopped again afterward.
