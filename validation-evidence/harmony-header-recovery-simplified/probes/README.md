# Simplified Harmony recovery probes

These probes validate commit `ae3fffc9d0ab0bbb7f311a02941f262ca62efea0` using
separate Python 3.12.14 environments with `openai-harmony==0.0.4` (`before`) and
`oss-harmony==0.0.12` (`after`). Those labels name library versions; both execute
the same final SGLang source. Source hashes are recorded in every result file.

The scripts AST-extract the actual helper functions and context classes, without
modifying their implementation, and bind the real Harmony library. This avoids
unrelated server/GPU imports. These are isolated checks, **not full-runtime or
GPU-serving tests**. A small test facade in `module_probe.py` only forwards calls
to the extracted context methods; production has no parser wrapper.

## Functional results

Both library versions pass:

- Four valid-stream controls with unchanged native tokens, messages, state and
  partial content.
- Three metadata-corruption recoveries and three unrecognized-header errors.
- Four missing-delimiter recoveries preserving deliberately noncanonical,
  character-by-character argument tokenization, including literal control text.
- Eleven invalid missing-delimiter cases remain unrecovered (unknown recipients,
  invalid/non-object/truncated JSON, authored text, non-call endings, etc.).
- Three prior/current messages appear exactly once across two different repairs;
  valid tool/assistant continuation brings the total to five.
- Two explicit initial assistant-header recoveries and two nested-header
  rejections.
- Thirty whole-output versus streaming comparisons: five histories, cumulative
  and incremental output, and chunk sizes 1, 4 and 11. Original processed-token
  counts remain unchanged by replay.

Raw results: `before-module.json`, `after-module.json`.

## CPU microbenchmark

`benchmark_context.py` compares ordinary `StreamableParser.process` against the
actual `HarmonyContext._process_token` fast path. Parser/context construction and
fixture encoding are outside the timed processing loops. Ten repetitions
alternate native/context order. The failure benchmark separately times a
metadata error plus recovery, or terminal missing-message recovery, after the
prior history has already been parsed.

All timings are medians in milliseconds. These measurements describe parser CPU
work only and do not imply serving throughput or GPU performance.

| Library | Body tokens | Native processing | Context processing |
| --- | ---: | ---: | ---: |
| openai-harmony 0.0.4 | 1,000 | 0.189 | 0.211 |
| openai-harmony 0.0.4 | 10,000 | 1.362 | 1.540 |
| oss-harmony 0.0.12 | 1,000 | 0.549 | 0.537 |
| oss-harmony 0.0.12 | 10,000 | 5.098 | 5.685 |

The small negative difference in the 1,000-token oss-harmony case is measurement
noise, not an asserted improvement.

| Library | Prior body tokens | Metadata recovery | Missing-message recovery |
| --- | ---: | ---: | ---: |
| openai-harmony 0.0.4 | 0 | 0.364 | 1.395 |
| openai-harmony 0.0.4 | 1,000 | 0.600 | 2.771 |
| openai-harmony 0.0.4 | 10,000 | 1.883 | 4.115 |
| oss-harmony 0.0.12 | 0 | 0.331 | 1.368 |
| oss-harmony 0.0.12 | 1,000 | 1.159 | 3.809 |
| oss-harmony 0.0.12 | 10,000 | 7.226 | 9.269 |

Recovery replays the entire retained history. Its cost grows with that history;
repeated recovery can accumulate quadratic work across a growing conversation.
This is the explicit tradeoff for eliminating parallel parser state/history.
Raw timing samples are in `before-benchmark.json` and `after-benchmark.json`;
`summary.json` contains source hashes and compact medians.

## Reproduce

Run with an interpreter containing the desired Harmony distribution and orjson.
The old library needs its vocabulary cached or otherwise accessible. Supply the
SGLang source checkout as the sole positional argument:

```bash
/path/to/venv/bin/python module_probe.py /path/to/sglang
/path/to/venv/bin/python benchmark_context.py /path/to/sglang
```

Run the commands separately for each library. Both probes exit zero on success.
