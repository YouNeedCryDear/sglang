# Native Harmony library validation

Validated SGLang commit `afbe4d556217b6cc9668aeea1ec58fec1d592020` with separate
Python 3.12.14 environments containing `openai-harmony==0.0.4` and
`oss-harmony==0.0.12`. Full installed versions and source SHA256 values are in
[metadata.json](metadata.json). Both distributions expose `openai_harmony`.
The candidate `harmony_utils.py` is byte-identical to SGLang base
`a4bef204c51e1c1b7ed59593b85993a940367591`; the legacy rewrite helper is removed.

## Results

- SGLang native rendering matches direct oss-harmony rendering in all **11/11**
  fixtures, including exact token IDs and decoded text.
- Old 0.0.4 and native 0.0.12 rendering match in **7/11** fixtures. Four tool
  headers intentionally differ, as shown below and in
  [comparison.json](comparison.json). This is not a claim of identical model
  input tokens across the dependency migration.
- For the same **11 old token streams**, the libraries return identical parsed
  messages in both whole-message and token-at-a-time modes: **22 matching parser
  results per library**. Separately, all **11 native token streams** parse
  successfully under 0.0.12, and their whole/streaming results agree. Native
  content-type metadata is not asserted equal to the old rendered metadata.
- The actual four-case SGLang native-header/body regression passes on the final
  source and fails all four subcases with the saved previous legacy shim. It
  also fails all four subcases with 0.0.4. The body includes literal
  `<|start|>assistant to=python` text and UTF-8 `café`; body tokens stay ordinary
  text and remain intact.
- With an empty vocabulary cache and `socket` syscalls denied by Linux seccomp,
  old 0.0.4 fails to load, while 0.0.12 loads and round-trips UTF-8 without
  creating cache files. A separate closed-localhost-proxy subprocess check also
  fails for old 0.0.4 and succeeds for 0.0.12.

| Fixture | Old/native equal | Final/native equal |
| --- | --- | --- |
| plain | yes | yes |
| tools schema | yes | yes |
| analysis | yes | yes |
| final | yes | yes |
| commentary text | yes | yes |
| commentary/function call | no: channel precedes recipient | yes |
| commentary/function JSON | no: channel order and constrain marker | yes |
| analysis/python | yes | yes |
| analysis/python code | no: constrain marker added | yes |
| analysis/browser JSON | no: constrain marker added | yes |
| analysis/browser | yes | yes |

These header changes are intentional in upstream
[commit c16672a](https://github.com/oss-harmony/harmony/commit/c16672a4613d3e2550758ad3630e5ed79da8301b).
The rendering part of
[vLLM PR #59387](https://github.com/vllm-project/vllm/pull/59387), inspected at
head `756ee24f369475638e4bb887828fa45333425864`, likewise removes its legacy
rewrite. Its independent malformed-header parser repairs are outside this
SGLang change. No newer Harmony API or dependency release is needed to use
native 0.0.12 rendering.

## Scope and files

These are isolated library checks, not GPU serving tests. The SGLang rendering
functions and the durable regression method are extracted unchanged by Python
AST and executed with the real installed library, to avoid unrelated server/GPU
imports. The complete SGLang test file and serving requests are exercised
separately in the GPU evidence. No parser recovery logic is implemented here.

- `before.json`, `after.json`: direct old/native render tokens and text.
- `before-sglang.json`, `after-sglang.json`: actual final SGLang rendering
  functions under each distribution.
- `before-parse.json`, `after-parse.json`: both parser modes applied to the same
  old token streams; `after-native-parse.json` applies both modes to native
  streams. The open next-assistant completion prefix is removed before parsing.
- `after-body.log` and `after-body.stderr.log`: actual new regression passes.
- `after-body-legacy-shim.log` and matching stderr: regression fails with the
  saved pre-removal production source `harmony_utils_with_legacy_shim.py`.
- `before-offline.log`, `after-offline.log`: seccomp offline results.
- `before-proxy.json`, `after-proxy.json`: subprocess return codes under invalid
  proxies, empty caches and cleared proxy bypasses.

## Reproduce

Create separate environments for `openai-harmony==0.0.4` and
`oss-harmony==0.0.12`. The libraries must not share an environment because they
provide the same import path. This directory is intended to live at
`validation-evidence/oss-harmony-native/library` in the source checkout. In that
layout, source paths resolve relative to this directory; otherwise set
`SGLANG_SOURCE_ROOT` to the source checkout.

```bash
HARMONY_BEFORE_PYTHON=/path/to/old-env/bin/python \
HARMONY_AFTER_PYTHON=/path/to/native-env/bin/python \
python3 validation-evidence/oss-harmony-native/library/run_probes.py
```

The first old-library render needs cached vocabularies or network access. The
offline checks subsequently create fresh caches. The seccomp check requires
Linux `libseccomp.so.2`; the proxy check needs permission to reserve a localhost
socket. Recorded runs were performed outside the tool sandbox, so the proxy
result does not depend on sandbox-wide network denial.

`run_probes.py` refreshes raw results, metadata and
`probe_exit_codes.json`, then runs `compare_probes.py`. Expected nonzero probe
exits are `before-body`, `before-offline`, and `after-body-legacy-shim`, each 1.
Every other probe exits 0. The proxy probe itself exits 0 and reports the child
exit in JSON: old child 1, native child 0. The runner exits 0 only when those
expectations and comparison assertions pass.
