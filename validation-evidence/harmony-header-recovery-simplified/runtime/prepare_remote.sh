set -eu
work=/tmp/oss-harmony-simplified-evidence-20261105
mkdir -p "$work/baseline" "$work/candidate"
for phase in baseline candidate; do
 sudo -n docker commit "oss-harmony-header-$phase-20261103" "oss-harmony-simplified-$phase:20261105" > "$work/$phase/runtime_image_id.txt"
 sudo -n docker run -d --name "oss-harmony-simplified-$phase-20261105" --runtime=runc -e NVIDIA_VISIBLE_DEVICES=void -v "$work":/work -w /work "oss-harmony-simplified-$phase:20261105" sleep infinity
 sudo -n docker exec "oss-harmony-simplified-$phase-20261105" python -c 'import json,platform,importlib.metadata as m,torch; from openai_harmony import load_harmony_encoding,HarmonyEncodingName; names=["sglang","torch","openai-harmony","oss-harmony","openai","transformers","sglang-kernel","tml-renderers","pytest","pytest-asyncio"]; versions={n:(m.version(n) if next(m.distributions(name=n),None) else None) for n in names}; versions["python"]=platform.python_version(); versions["architecture"]=platform.machine(); versions["cuda_available"]=torch.cuda.is_available(); versions["cuda_device_count"]=torch.cuda.device_count(); versions["harmony_probe_token_count"]=len(load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS).encode("hello")); print(json.dumps(versions,indent=2))' > "$work/$phase/environment_ready.json"
 cat "$work/$phase/environment_ready.json"
done
