set -eu
work=/tmp/oss-harmony-header-evidence
sudo -n docker start oss-harmony-header-baseline-20261103 oss-harmony-header-candidate-20261103
for phase in baseline candidate; do
 if [ "$phase" = baseline ]; then package=openai-harmony; else package=oss-harmony; fi
 for source in upstream fixed; do
  if [ "$source" = upstream ]; then commit=3f5b1bec8e00115bc8439b5b9a9da902822d2f82; else commit=75429de8959a18da1b316bc5947949ff1fae9184; fi
  sudo -n docker exec -e "PYTHONPATH=/work/source_$source/python" "oss-harmony-header-$phase-20261103" python /work/run_repro_context.py "$commit" "$package" > "$work/$phase/minimal_repro_$source.jsonl" 2> "$work/$phase/minimal_repro_$source.stderr"
  cat "$work/$phase/minimal_repro_$source.jsonl"
 done
done
sudo -n docker stop oss-harmony-header-baseline-20261103 oss-harmony-header-candidate-20261103
sudo -n tar -czf "$work/minimal-repro-results.tar.gz" -C "$work" baseline/minimal_repro_upstream.jsonl baseline/minimal_repro_fixed.jsonl candidate/minimal_repro_upstream.jsonl candidate/minimal_repro_fixed.jsonl
sudo -n chmod a+r "$work/minimal-repro-results.tar.gz"
nvidia-smi --query-gpu=index,name,memory.used,utilization.gpu --format=csv
nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv
