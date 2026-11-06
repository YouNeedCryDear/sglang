# Critical Harmony recovery tests — 2026-11-05

Final commit `e90d413945a0ac38b69b191cb855591abcb2ca26` passes both complete Responses suites with either Harmony distribution: **110 tests and 92 subtests passed** for `openai-harmony==0.0.4`, and the same counts for `oss-harmony==0.0.12`.

The two rewritten positive regression methods were also run against unchanged upstream production code with these same final tests. All **five subcases fail as expected** with either package: three non-streaming cases and two streaming cases. Full logs are included.

## Source and results

Production is byte-identical to `ae3fffc9d0ab0bbb7f311a02941f262ca62efea0`. Only `test_serving_responses.py` and `test_serving_responses_stream.py` changed. A fresh extraction of the existing exact production archive received only the two final test files. A separate tree used upstream `3f5b1bec8e00115bc8439b5b9a9da902822d2f82` plus those same final tests.

`tested_source_sha256.json` records the three unchanged production files and two revised test files. Their hashes were verified remotely and against the final commit. Both source trees were compiled and checked for absence of the deleted recovery-wrapper module; details are in each environment's `environment_and_source.json`. `upstream_with_final_tests_sha256.json` independently identifies the upstream reproduction tree.

| Environment | Final full suites | Rewritten regressions on upstream |
| --- | --- | --- |
| openai-harmony 0.0.4 (`baseline/`) | 110 tests + 92 subtests passed | 5 subcases failed as expected |
| oss-harmony 0.0.12 (`candidate/`) | 110 tests + 92 subtests passed | 5 subcases failed as expected |

Upstream spliced metadata returns an HTTP400 handler response; missing-separator variants omit the function call. Both streaming modes raise `HarmonyError`. Pytest summarizes the targeted upstream run as `5 failed, 2 passed`: the five failures are unittest subtests inside the two selected methods. This does not indicate successful upstream regression behavior.

The passing tests invoke the real Responses handler and Harmony parser with deterministic engine-token fixtures. Streaming tests consume the real SSE generator and verify successive repairs, output item identity/order and exact arguments in incremental and cumulative modes. The non-streaming tests retain the token-usage check.

## Initial attempt and correction

The first run at `e7467cd75e064a95b4a9516cb2fd300cb7b8e124` had 110 tests and 90 subtests pass, with two streaming subtests failing on a newly added usage assertion: actual output-token usage 0 versus expected 53. Existing `StreamingHarmonyContext` does not update that usage counter. The recovery outputs were already correct.

Only that unrelated streaming usage assertion was removed; production code was unchanged. The corrected streaming method then passed 1 test and 2 subtests under each package before the final full-suite run. Original failure logs and their source manifest/hashes are preserved under `initial_attempt/`; final results remain in `baseline/` and `candidate/`.

## Environment and commands

The existing isolated aarch64 CPU containers were reused with fresh source/results directories. Both used Docker `runc`, `NVIDIA_VISIBLE_DEVICES=void`, no GPU device requests, CUDA unavailable and device count zero. No model, network server, inference, minimal-reproduction rerun or benchmark was launched for this test-only change.

Base image: `lmsysorg/sglang:v0.5.23-cu130`, digest `sha256:f832b5c39559c9caa900b22ad37c76fcce66470676855c42052102c537812f1f`. Exact reused local image IDs are in `source_provenance.json` and per-environment `runtime_image_id.txt` files. These are local dependency snapshots, not published images.

Actual shared versions: Python 3.12.16, torch 2.14.1+cu130, transformers 5.19.0, sglang-kernel 0.4.10, openai 2.8.0, tml-renderers 0.1.0, pytest 9.2.0, pytest-asyncio 1.4.1.post1. Each `environment_and_source.json` records actual package versions. Its SGLang 0.5.23 field is image distribution metadata; execution used the source trees described above via `PYTHONPATH`. The old Harmony package used the existing vocabulary cache.

Both environments ran the complete suites:

```sh
cd /work/critical-tests-20261105/source
PYTHONPATH=/work/critical-tests-20261105/source/python python -m pytest -q \
  test/registered/unit/entrypoints/openai/test_serving_responses.py \
  test/registered/unit/entrypoints/openai/test_serving_responses_stream.py
```

The upstream check selected these exact methods under `PYTHONPATH=/work/critical-tests-20261105/source_upstream/python`:

```sh
python -m pytest -q \
  test/registered/unit/entrypoints/openai/test_serving_responses.py::HarmonyHeaderRecoveryTestCase::test_malformed_headers_recover_function_call_response \
  test/registered/unit/entrypoints/openai/test_serving_responses_stream.py::HarmonyStreamLifecycleTestCase::test_repaired_headers_preserve_function_call_stream
```

`run_remote_tests.sh` and `verify_environment.py` preserve exact execution and verification commands. Full suite, corrected streaming and source checks exited 0; upstream targeted checks exited 1 as expected. `summary.json` provides counts and `evidence_sha256.json` covers all evidence files.

Both reused CPU containers were stopped after collection. The host GPU was verified at 1 MiB, 0% utilization, with no compute processes. No lease was changed; prior source/evidence and unrelated workloads were preserved.
