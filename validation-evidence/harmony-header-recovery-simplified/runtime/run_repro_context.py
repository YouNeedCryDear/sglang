import importlib.metadata
import json
import runpy
import sys
import torch

print(json.dumps({'context': {'source_commit': sys.argv[1], 'harmony_distribution': sys.argv[2], 'harmony_version': importlib.metadata.version(sys.argv[2]), 'cuda_available': torch.cuda.is_available(), 'cuda_device_count': torch.cuda.device_count()}}), flush=True)
runpy.run_path('/work/reproduce.py', run_name='__main__')
