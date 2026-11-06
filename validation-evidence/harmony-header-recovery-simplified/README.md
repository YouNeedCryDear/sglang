# Simplified Harmony header recovery validation

Tested source: `ae3fffc9d0ab0bbb7f311a02941f262ca62efea0`.
Upstream comparison: `3f5b1bec8e00115bc8439b5b9a9da902822d2f82`.
Draft fix: [sgl-project/sglang#48297](https://github.com/sgl-project/sglang/pull/48297).
Related dependency migration: [sgl-project/sglang#48267](https://github.com/sgl-project/sglang/pull/48267).

## Design and results

The fix uses SGLang's existing native parser factory and context lifecycle. Two stateless recovery helpers in `harmony_utils.py` inspect retained tokens only after a parsing error or at generation completion. They repair a recognized header and replay its corrected history into a temporary native parser, replacing the current parser only after successful replay. There is no separate recovery module or parser proxy, and no duplicate token/message history. Compared with the previous draft, production code decreases by 65 lines. One new regression method adds six subcases for successive repairs, terminal idempotence and partial-content preservation.

Both complete Responses suites passed **112 tests and 122 subtests with each package**, `openai-harmony==0.0.4` and `oss-harmony==0.0.12`. Four minimal-reproduction runs cover upstream/fixed source with both packages: upstream produces a metadata `HarmonyError` or drops the missing-separator call; fixed source produces `echo({"x":1})` for both streams.

Read [runtime/CPU_README.md](runtime/CPU_README.md) for the exact environment, source hashes, setup, commands and logs. These tests use the actual Responses handler, Harmony parser and SSE generator, with only generated token delivery stubbed. They ran in CPU-only containers with CUDA unavailable, without model weights, inference, or a network server. The containers were stopped after collection.

The [unchanged upstream regression failures](https://github.com/YouNeedCryDear/sglang/tree/7acb903a4d0ca0d83fc7078702bcd6a09481e8ec/validation-evidence/harmony-header-recovery/runtime) remain available from the previous validation: 20 failing subcases within the two unchanged positive methods, for either library. Previous wrapper timings do not describe this revision.

## Supplemental checks and CPU timings

[probes/README.md](probes/README.md) documents isolated checks that AST-extract the actual helper/context definitions and bind the real native Harmony libraries. These are supplemental to the full-runtime suites, not substitutes for them. They include valid native-stream parity, strict rejection guards, explicit/nested header cases, exact argument-token preservation, repeated recovery and continuation, plus 30 whole-output versus streaming comparisons per library.

The isolated microbenchmark measures native processing versus the actual context token-processing method, excluding construction and encoding. With 10,000 valid body tokens, median added time is **0.178 ms** for openai-harmony and **0.587 ms** for oss-harmony. Metadata recovery with 10,000 preceding body tokens takes **1.883 / 7.226 ms** (old/oss); terminal missing-message recovery takes **4.115 / 9.269 ms**. These are local CPU measurements with ten alternating processing repetitions. They are not serving throughput/latency or model-accuracy results.

Full-history replay costs O(history length) per recovery; repeated repairs over growing history can accumulate quadratic work. The normal path does not scan or copy token history.

[static_checks.json](static_checks.json) records passing applicable pre-commit hooks, `git diff --check`, and a clean merge-tree check with migration commit `dc4d6e600a9e87cc3a979209c74dc657557bc0cb`. The record captures observed outcomes rather than raw stdout. [SHA256SUMS.json](SHA256SUMS.json) binds the evidence files; runtime and probe records separately bind results to the tested source.

No natural malformed-header frequency, broad model accuracy, or GPU inference performance claim is made. Evidence is on a separate branch and does not enter the fix's source diff.
