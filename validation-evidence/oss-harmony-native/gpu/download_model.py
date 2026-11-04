import json
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download
repo='openai/gpt-oss-20b'
info=HfApi().model_info(repo,revision='6cee5e81ee83917806bbde320786a8fb61efebee')
Path('/work/model_revision.json').write_text(json.dumps({'repo':repo,'revision':info.sha},indent=2))
path=snapshot_download(repo_id=repo,revision=info.sha,allow_patterns=['*.json','*.safetensors','*.jinja','*.tiktoken'],ignore_patterns=['original/*'])
Path('/work/model_path.txt').write_text(path)
print(path,flush=True)
