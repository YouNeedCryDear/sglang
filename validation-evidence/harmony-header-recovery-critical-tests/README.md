# Critical Harmony recovery regressions

Source: `e90d413945a0ac38b69b191cb855591abcb2ca26`.
Draft fix: [sgl-project/sglang#48297](https://github.com/sgl-project/sglang/pull/48297).
Related migration: [sgl-project/sglang#48267](https://github.com/sgl-project/sglang/pull/48267).

This revision trims the added coverage from six methods and 41 subtests to four methods and 11 subtests, plus one standalone partial-content case. It removes 163 net test lines. All pre-existing test functions remain unchanged. Production code is identical to `ae3fffc9d0ab0bbb7f311a02941f262ca62efea0`.

The retained tests cover:

- Three malformed headers through the non-streaming Responses handler, preserving earlier reasoning, argument text and original completion-token usage.
- Six rejection guards: undeclared functions, no tools, builtin recipients, truncated JSON, non-call endings and authored metadata.
- Unfinished content remaining unfinished at terminal notification.
- Successive repairs through streaming Responses, with cumulative and incremental token delivery, preserving item order, IDs, argument deltas and terminal output.

Both complete Responses suites pass **110 tests and 92 subtests** with each of `openai-harmony==0.0.4` and `oss-harmony==0.0.12`. The two positive methods fail in five subcases against upstream production at `3f5b1bec8e00115bc8439b5b9a9da902822d2f82` with either package.

See [runtime/CPU_README.md](runtime/CPU_README.md) for commands, environment, source hashes and raw logs. The real handler, Harmony parser and SSE generator run with deterministic engine-token fixtures in CPU-only containers on an existing leased host. No GPU inference or model benchmark is involved. [precommit.log](precommit.log) records passing applicable hooks; `git diff --check` also passed.

The [prior reproduction and parser measurements](https://github.com/YouNeedCryDear/sglang/tree/b94793e56f0973ae11f5304599a4a98f5384440e/validation-evidence/harmony-header-recovery-simplified) remain applicable to the unchanged production code. They were not rerun for this test-only reduction. The runtime evidence also records an initial test attempt: a newly added streaming-usage assertion hit pre-existing zero-token accounting and was removed to keep this change scoped to header recovery. The non-streaming usage assertion remains.
