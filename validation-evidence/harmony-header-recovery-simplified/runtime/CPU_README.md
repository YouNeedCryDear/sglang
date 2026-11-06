# Simplified Harmony recovery validation — 2026-11-05

The frozen simplified implementation passes both complete Responses suites with either Harmony distribution: **112 tests and 122 subtests passed** for `openai-harmony==0.0.4`, and the same counts for `oss-harmony==0.0.12`.

The unchanged minimal reproduction was rerun against both upstream and fixed source in both environments. Upstream raises `HarmonyError` for spliced metadata and drops the missing-separator call (`output: []`). The simplified source returns the expected `echo({"x":1})` function call for both cases with either package.

## Source verification

- Upstream source: `3f5b1bec8e00115bc8439b5b9a9da902822d2f82`.
- Tested simplified source: `ae3fffc9d0ab0bbb7f311a02941f262ca62efea0`.
- The fixed source was transferred as an **exact full git archive** and extracted into a fresh directory. No previous source overlay was reused.
- All five changed files against upstream were SHA256-verified remotely, compiled successfully in each environment, and matched to the frozen commit. See `tested_source_sha256.json` and each environment's `source_verification.json`.
- The deleted `python/sglang/srt/entrypoints/harmony_recovery.py` wrapper was verified absent in both test environments.
- `source_provenance.json` records the archive hash, commit IDs, changed-file hashes, dependency-image IDs and cleanup state.

The `baseline/` directory denotes the **openai-harmony 0.0.4 environment**; `candidate/` denotes **oss-harmony 0.0.12**. Both environments ran exactly the same simplified source and full suites.

## Results

| Harmony distribution | Full Responses suites | Minimal reproduction against upstream | Minimal reproduction against fixed source |
| --- | --- | --- | --- |
| openai-harmony 0.0.4 | 112 tests + 122 subtests passed | Parser error / missing call | Both return expected function call |
| oss-harmony 0.0.12 | 112 tests + 122 subtests passed | Parser error / missing call | Both return expected function call |

The full suites exercise the real `create_responses` handler and Harmony parser with tokenizer-manager generation stubbed to supply deterministic token streams. Streaming cases consume the real SSE generator. Coverage includes malformed headers, declared-tool/JSON guards, preservation of literal Harmony-looking body text and original argument tokens, surrounding output, SSE identity/order/deltas, and successive repairs with completed or partial trailing content in non-streaming, cumulative and incremental modes.

`reproduce.py` is unchanged from the prior publication check. It directly exercises the real Harmony context and output parser without model inference. The four `minimal_repro_{upstream,fixed}.jsonl` files retain the exact script output; only their first record is added by `run_repro_context.py` to record source commit, package/version and CUDA availability. Each file's next two records are unmodified script results.

This run did not repeat the earlier targeted full-API upstream failure suite. The current bundle contains fresh full-suite results for the simplified source and fresh minimal upstream/fixed reproductions. Earlier evidence was preserved separately.

## Runtime

Both isolated containers ran on the existing aarch64 host with `--runtime=runc -e NVIDIA_VISIBLE_DEVICES=void`, without a GPU device request. Both recorded CUDA unavailable and device count zero. No model, network API server, GPU kernel or model inference was launched.

Base image: `lmsysorg/sglang:v0.5.23-cu130`, digest `sha256:f832b5c39559c9caa900b22ad37c76fcce66470676855c42052102c537812f1f`. The two preserved dependency environments were snapshotted locally into fresh task containers; their exact image IDs are recorded in `baseline/runtime_image_id.txt`, `candidate/runtime_image_id.txt` and `source_provenance.json`. These are local snapshots, not published images.

Shared versions: Python `3.12.16`, torch `2.14.1+cu130`, transformers `5.19.0`, sglang-kernel `0.4.10`, openai `2.8.0`, tml-renderers `0.1.0`, pytest `9.2.0`, pytest-asyncio `1.4.1.post1`. Per-environment `environment_ready.json` records actual distributions and successful encoding probes. Its SGLang `0.5.23` value is image distribution metadata; executed source came from `PYTHONPATH` at the commits above. The original package used the retained standard vocabulary cache; this is not an offline installation test.

## Commands

Exact source archive preparation:

```sh
git archive --format=tar.gz -o source-ae3fffc9.tar.gz ae3fffc9d0ab0bbb7f311a02941f262ca62efea0
```

Both environments ran:

```sh
python /work/verify_source.py
cd /work/source_fixed
PYTHONPATH=/work/source_fixed/python python -m pytest -q \
  test/registered/unit/entrypoints/openai/test_serving_responses.py \
  test/registered/unit/entrypoints/openai/test_serving_responses_stream.py
```

The unchanged short reproduction was run with both source trees:

```sh
PYTHONPATH=/work/source_upstream/python python /work/reproduce.py
PYTHONPATH=/work/source_fixed/python python /work/reproduce.py
```

`prepare_remote.sh`, `run_remote_tests.sh`, `verify_source.py`, `run_repro_context.py` and `finalize_remote.sh` preserve the exact environment preparation, source verification, execution and collection commands. Each environment directory contains full pytest output, raw reproduction JSONL, source-verification output and exit codes. All recorded checks exited zero. `summary.json` and `evidence_sha256.json` provide machine-readable results and file hashes.

Both new CPU containers were stopped after collection. No lease was changed, and prior evidence and unrelated workloads were left intact. The host GPU was verified afterward at 1 MiB, 0% utilization, with no compute processes. Artifacts were retained.

These deterministic tests establish the covered parser and SSE behavior; they do not measure natural malformed-header frequency, broad model accuracy, throughput or latency.
