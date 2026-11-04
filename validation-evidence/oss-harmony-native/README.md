# Native oss-harmony migration validation

Run date: November 3, 2026 (America/Los_Angeles).

Candidate: `afbe4d556217b6cc9668aeea1ec58fec1d592020`, based on `a4bef204c51e1c1b7ed59593b85993a940367591`.

This revision uses `oss-harmony==0.0.12` without a legacy rendering adapter. Its Python runtime source is identical to the base commit; the final PR changes six dependency manifests, documentation, and regression tests.

## Intended behavior

The recipient ordering on commentary messages and explicit `<|constrain|>` content-type markers are intentional changes in [oss-harmony commit c16672a](https://github.com/oss-harmony/harmony/commit/c16672a4613d3e2550758ad3630e5ed79da8301b). They are already included in version 0.0.12. This revision follows the native-rendering portion of [vLLM PR #59387](https://github.com/vllm-project/vllm/pull/59387), inspected while open at `756ee24f369475638e4bb887828fa45333425864`. Its separate malformed-header parser recoveries are outside this migration.

The earlier evidence for commit `3d1442e` tested a legacy adapter. It does not describe this final revision. Token-for-token compatibility with `openai-harmony==0.0.4` is not the intended contract: native rendering changes four of eleven captured fixtures.

## Library checks

- Final SGLang rendering matches native `oss-harmony==0.0.12` for **11/11 fixtures**. Seven match the old package; four intentionally differ. [Comparison](library/comparison.json).
- The actual four-case native-header/body regression passes with the final source, and fails with the removed adapter. The body includes Unicode and literal control-token text.
- The same eleven old token streams produce matching full and incremental parse results under both packages (**22 comparisons**). This is parser compatibility for fixed old input, not old/native prompt equivalence.
- With an empty vocabulary cache and Linux seccomp blocking socket creation, the old package fails and the new package loads and encodes/decodes successfully. The new cache remains empty.

See [library reproduction instructions](library/README.md) for raw results, separate environment versions, expected failure exit codes, and portable scripts. Isolated source probes extract the actual functions/test via AST to avoid unrelated GPU imports. Full-runtime unit and GPU checks are recorded separately below.

## GPU checks

Fresh validation used one initially idle NVIDIA GB300 on an existing Colossus lease, with `openai/gpt-oss-20b` MXFP4 at revision `6cee5e81ee83917806bbde320786a8fb61efebee`. Both phases used the ARM64 `lmsysorg/sglang:v0.5.23-cu130` image with the tested source overlaid through `PYTHONPATH`, holding other dependencies fixed.

| Check | Before: openai-harmony 0.0.4 | After: native oss-harmony 0.0.12 |
| --- | --- | --- |
| Responses unit suites | 106 tests + 81 subtests passed | 108 tests + 85 subtests passed |
| GPU API cases | 16/16 passed, all HTTP 200 | 16/16 passed, all HTTP 200 |
| Identical requests | Reference | 16/16 |
| Exact answer text | Reference | 14/16 |
| Normalized final responses | Reference | 10/16 |

The matrix covers plain Responses generation, function calls, explicit tool-result replay, Chat Completions, and a third tool call/result after two earlier tool turns, each streaming and non-streaming. Semantic checks verify tool names/arguments and the supplied weather facts.

The two changed answers are the single-tool replay cases: wording differs while the supplied `21 C` and `sunny` facts remain correct. Four multi-turn cases keep the expected Rome tool call/result but differ in reasoning or usage. These observations accompany the intentional prompt changes; this revision does not claim identical generations or normalized responses across every case. [Case-by-case comparison](gpu/comparison.json).

Normalization excludes generated identifiers, timestamps, and cache-hit counts. It does not require identical SSE event IDs or chunk boundaries. See [exact environment and reproduction instructions](gpu/GPU_README.md), [baseline unit log](gpu/baseline_unit.log), and [candidate unit log](gpu/candidate_unit.log). Raw requests, final responses, and SSE events are retained under [baseline](gpu/baseline) and [candidate](gpu/candidate).

The old package needed a manually populated vocabulary cache after its automatic download failed on the fresh machine. The separate empty-cache tests above verify the new package's offline behavior. Both validation servers were stopped and the GPU freed after the run; the lease was not changed.

## Other checks and limits

- All applicable changed-file pre-commit hooks passed: [log](precommit.log).
- `git diff --check` passed; there are no runtime-source changes relative to the base.
- The deployment documentation and six dependency pins are unchanged from the initial migration. Mintlify validation remains unrun locally because `mint` and `npx` are unavailable.
- No serving-throughput or model-accuracy benchmark is claimed. The measurements of the deleted helper in the earlier evidence are no longer relevant.
- Scope is the Python serving runtime. Rust model-gateway packaging and malformed-output parser recovery are unchanged.
