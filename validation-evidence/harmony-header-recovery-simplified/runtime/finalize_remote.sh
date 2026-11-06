set -eu
work=/tmp/oss-harmony-simplified-evidence-20261105
for phase in baseline candidate; do
 test -f "$work/$phase/all_finished"
 for check in source_verification fixed_full_suites minimal_repro_upstream minimal_repro_fixed; do
  test "$(cat "$work/$phase/$check.exit")" = 0
 done
done
sudo -n tar -czf "$work/results.tar.gz" -C "$work" baseline candidate tested_source_sha256.json
sudo -n chmod a+r "$work/results.tar.gz"
sudo -n docker stop oss-harmony-simplified-baseline-20261105 oss-harmony-simplified-candidate-20261105
nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv
nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv
