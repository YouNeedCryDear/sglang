# SGLang Harmony malformed-header recovery evidence

Fixed source: `75429de8959a18da1b316bc5947949ff1fae9184`.
Upstream source: `3f5b1bec8e00115bc8439b5b9a9da902822d2f82`.

This evidence accompanies a separate output-parser recovery fix. Related dependency/native-rendering migration: [sgl-project/sglang#48267](https://github.com/sgl-project/sglang/pull/48267). Recovery is inspired by [vLLM#59387](https://github.com/vllm-project/vllm/pull/59387), commit `756ee24f369475638e4bb887828fa45333425864`.

## Functional validation

The two complete Responses unit suites passed **111 tests and 116 subtests with each package**, `openai-harmony==0.0.4` and `oss-harmony==0.0.12`. The same new positive tests fail in **20 subcases** on unchanged upstream production source with either package. They expose spliced-metadata parser errors, dropped calls when the message separator is absent, and analysis-channel functions incorrectly emitted as reasoning.

Read [runtime/CPU_README.md](runtime/CPU_README.md) for source provenance, exact setup, test commands and limitations. [runtime/summary.json](runtime/summary.json) provides counts. Full logs and environment records are under [runtime/baseline](runtime/baseline) (openai-harmony) and [runtime/candidate](runtime/candidate) (oss-harmony). Only deterministic model-generated tokens are stubbed: the tests use the actual Responses handler, Harmony parser and SSE generator.

The [minimal reproduction script](runtime/reproduce.py) was separately verified against both source revisions with both packages. Run it in an installed SGLang environment from the checkout you want to inspect:

```sh
PYTHONPATH="$PWD/python" python /absolute/path/to/reproduce.py
```

Upstream reports `HarmonyError` for spliced metadata and an empty output list for the missing separator. The fixed source emits a function call named `echo`, with arguments `{"x":1}`, for both. Four `minimal_repro_*.jsonl` files capture the results and execution context.

Tests ran in CPU-only containers on an existing leased aarch64 host, with no model/server launch and CUDA unavailable. Both containers were stopped after collection. These runs do not measure natural malformed-header incidence, broad model accuracy, model inference throughput or live HTTP/network behavior.

## Native parser probes and timing

[library/module_probe.py](library/module_probe.py) covers valid-stream parity, both repairs, rejection guards, exact argument-token preservation, prior-message preservation, repeated finalization and continuation. `before-*` files use openai-harmony 0.0.4; `after-*` files use oss-harmony 0.0.12. Both compare the unchanged native parser with the final recovering wrapper, not different source implementations.

[library/benchmark_valid.py](library/benchmark_valid.py) records all timing samples; [library/final-summary.json](library/final-summary.json) summarizes them. The wrapper adds approximately **0.56 ms** (openai-harmony) and **0.64 ms** (oss-harmony) when processing 10,000 valid body tokens. Median construction overhead is approximately 0.002–0.006 ms. This is a local Python parser microbenchmark with alternating execution order and ten processing repetitions, not a serving throughput/latency benchmark. The only change to the published helper scripts is resolving the source module relative to this evidence checkout instead of its original temporary worktree path. Recorded measurement files are unmodified.

[precommit.log](precommit.log) records the passing applicable repository hooks. The source diff also passes `git diff --check` and merges cleanly with the migration PR's source commit `afbe4d556217b6cc9668aeea1ec58fec1d592020` (verified with `git merge-tree --write-tree`, without changing either branch).

[SHA256SUMS.json](SHA256SUMS.json) hashes every evidence file except itself; [runtime/tested_source_sha256.json](runtime/tested_source_sha256.json) binds runtime results to the six changed source/test files. Evidence is kept on a separate branch and is not included in the fix's source diff.
