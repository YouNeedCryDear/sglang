set -eu
work=/tmp/oss-harmony-simplified-evidence-20261105/critical-tests-20261105
for phase in baseline candidate; do
 test -f "$work/$phase/all_finished"
 test "$(cat "$work/$phase/verification.exit")" = 0
 test "$(cat "$work/$phase/fixed_full_suites.exit")" = 0
 test "$(cat "$work/$phase/corrected_streaming_targeted.exit")" = 0
 test "$(cat "$work/$phase/upstream_targeted.exit")" = 1
 tail -4 "$work/$phase/upstream_targeted.log"
done
sudo -n tar -czf "$work/final-results.tar.gz" -C "$work" baseline candidate tested_source_sha256.json upstream_with_final_tests_sha256.json source_manifest.json
sudo -n chmod a+r "$work/final-results.tar.gz"
sudo -n docker stop oss-harmony-simplified-baseline-20261105 oss-harmony-simplified-candidate-20261105
nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv
nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv
