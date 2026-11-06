set -eu
work=/tmp/oss-harmony-simplified-evidence-20261105
mkdir -p "$work/source_fixed" "$work/source_upstream"
test ! -e "$work/source_fixed/python/sglang/srt/entrypoints/harmony_recovery.py"
tar -xzf "$work/source-ae3fffc9.tar.gz" -C "$work/source_fixed"
tar -xzf /tmp/oss-harmony-header-evidence/upstream-3f5b1bec.tar.gz -C "$work/source_upstream"
for phase in baseline candidate; do
 if [ "$phase" = baseline ]; then package=openai-harmony; else package=oss-harmony; fi
 sudo -n docker exec -d "oss-harmony-simplified-$phase-20261105" sh -c "python /work/verify_source.py > /work/$phase/source_verification.json 2> /work/$phase/source_verification.stderr; echo \$? > /work/$phase/source_verification.exit; cd /work/source_fixed; PYTHONPATH=/work/source_fixed/python python -m pytest -q test/registered/unit/entrypoints/openai/test_serving_responses.py test/registered/unit/entrypoints/openai/test_serving_responses_stream.py > /work/$phase/fixed_full_suites.log 2>&1; echo \$? > /work/$phase/fixed_full_suites.exit; PYTHONPATH=/work/source_upstream/python python /work/run_repro_context.py 3f5b1bec8e00115bc8439b5b9a9da902822d2f82 $package > /work/$phase/minimal_repro_upstream.jsonl 2> /work/$phase/minimal_repro_upstream.stderr; echo \$? > /work/$phase/minimal_repro_upstream.exit; PYTHONPATH=/work/source_fixed/python python /work/run_repro_context.py ae3fffc9d0ab0bbb7f311a02941f262ca62efea0 $package > /work/$phase/minimal_repro_fixed.jsonl 2> /work/$phase/minimal_repro_fixed.stderr; echo \$? > /work/$phase/minimal_repro_fixed.exit; touch /work/$phase/all_finished"
done
