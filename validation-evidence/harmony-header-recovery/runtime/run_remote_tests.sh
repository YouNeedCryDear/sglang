set -eu
work=/tmp/oss-harmony-header-evidence
mkdir -p "$work/source_fixed" "$work/source_upstream"
tar -xzf "$work/upstream-3f5b1bec.tar.gz" -C "$work/source_fixed"
tar -xzf "$work/upstream-3f5b1bec.tar.gz" -C "$work/source_upstream"
tar -xzf "$work/fixed-overlay.tar.gz" -C "$work/source_fixed"
for name in test_serving_responses.py test_serving_responses_stream.py; do
 cp "$work/source_fixed/test/registered/unit/entrypoints/openai/$name" "$work/source_upstream/test/registered/unit/entrypoints/openai/$name"
done
python3 - <<'PY'
import pathlib,json,hashlib
root=pathlib.Path('/tmp/oss-harmony-header-evidence')
expected=json.loads((root/'tested_source_sha256.json').read_text())
assert all(hashlib.sha256((root/'source_fixed'/p).read_bytes()).hexdigest()==h for p,h in expected.items())
print('All six source hashes verified remotely.')
PY
for phase in baseline candidate; do
 sudo -n docker exec -d "oss-harmony-header-$phase-20261103" sh -c "cd /work/source_fixed; PYTHONPATH=/work/source_fixed/python python -m pytest -q test/registered/unit/entrypoints/openai/test_serving_responses.py test/registered/unit/entrypoints/openai/test_serving_responses_stream.py > /work/$phase/fixed_full_suites.log 2>&1; echo \$? > /work/$phase/fixed_full_suites.exit; cd /work/source_upstream; PYTHONPATH=/work/source_upstream/python python -m pytest -q test/registered/unit/entrypoints/openai/test_serving_responses.py::HarmonyHeaderRecoveryTestCase::test_malformed_headers_recover_function_call_response test/registered/unit/entrypoints/openai/test_serving_responses_stream.py::HarmonyStreamLifecycleTestCase::test_repaired_headers_preserve_function_call_stream > /work/$phase/upstream_targeted.log 2>&1; echo \$? > /work/$phase/upstream_targeted.exit"
done
