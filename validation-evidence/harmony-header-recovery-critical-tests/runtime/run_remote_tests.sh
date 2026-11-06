set -eu
work=/tmp/oss-harmony-simplified-evidence-20261105/critical-tests-20261105
mkdir -p "$work/source_upstream"
tar -xzf /tmp/oss-harmony-header-evidence/upstream-3f5b1bec.tar.gz -C "$work/source_upstream"
tar -xzf "$work/final-tests.tar.gz" -C "$work/source"
tar -xzf "$work/final-tests.tar.gz" -C "$work/source_upstream"
sudo -n docker start oss-harmony-simplified-baseline-20261105 oss-harmony-simplified-candidate-20261105
for phase in baseline candidate; do
 rm -f "$work/$phase/verification.exit" "$work/$phase/fixed_full_suites.exit" "$work/$phase/upstream_targeted.exit" "$work/$phase/all_finished"
 sudo -n docker exec -d "oss-harmony-simplified-$phase-20261105" sh -c "work=/work/critical-tests-20261105; python \$work/verify_environment.py > \$work/$phase/environment_and_source.json 2> \$work/$phase/verification.stderr; echo \$? > \$work/$phase/verification.exit; cd \$work/source; PYTHONPATH=\$work/source/python python -m pytest -q test/registered/unit/entrypoints/openai/test_serving_responses.py test/registered/unit/entrypoints/openai/test_serving_responses_stream.py > \$work/$phase/fixed_full_suites.log 2>&1; echo \$? > \$work/$phase/fixed_full_suites.exit; cd \$work/source_upstream; PYTHONPATH=\$work/source_upstream/python python -m pytest -q test/registered/unit/entrypoints/openai/test_serving_responses.py::HarmonyHeaderRecoveryTestCase::test_malformed_headers_recover_function_call_response test/registered/unit/entrypoints/openai/test_serving_responses_stream.py::HarmonyStreamLifecycleTestCase::test_repaired_headers_preserve_function_call_stream > \$work/$phase/upstream_targeted.log 2>&1; echo \$? > \$work/$phase/upstream_targeted.exit; touch \$work/$phase/all_finished"
done
