import importlib.metadata
import importlib.util
import json
import statistics
import time
from pathlib import Path
from openai_harmony import HarmonyEncodingName, Role, StreamableParser, load_harmony_encoding

source=Path(__file__).resolve().parents[3] / 'python/sglang/srt/entrypoints/harmony_recovery.py'
spec=importlib.util.spec_from_file_location('harmony_recovery',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
encoding=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
classes={'native':lambda:StreamableParser(encoding,role=Role.ASSISTANT),
         'recovering':lambda:module.RecoveringHarmonyParser(encoding,function_names={'echo'})}
results={'repeats':10,'unit':'milliseconds','construction':{},'processing':{}}
for distribution in ('openai-harmony','oss-harmony'):
    try:results['distribution']={distribution:importlib.metadata.version(distribution)}
    except importlib.metadata.PackageNotFoundError:pass
for name,factory in classes.items():
    samples=[]
    for repeat in range(20):
        start=time.perf_counter()
        parsers=[factory() for _ in range(50)]
        samples.append((time.perf_counter()-start)*1000/len(parsers))
    results['construction'][name]={'median_ms':statistics.median(samples),'samples_ms':samples}
for size in (1000,10000):
    tokens=encoding.encode('<|channel|>final<|message|>',allowed_special='all')+encoding.encode(' hello',disallowed_special=())*size+encoding.encode('<|return|>',allowed_special='all')
    timings={name:[] for name in classes}
    for repeat in range(10):
        # Alternate execution order to reduce ordering bias.
        for name in (list(classes) if repeat%2==0 else list(reversed(classes))):
            parser=classes[name]()
            start=time.perf_counter()
            for token in tokens:parser.process(token)
            elapsed=(time.perf_counter()-start)*1000
            timings[name].append(elapsed)
            assert len(parser.messages)==1
            assert parser.tokens==tokens
    medians={name:statistics.median(samples) for name,samples in timings.items()}
    results['processing'][str(size)]={'body_tokens':size,'total_tokens':len(tokens),'median_ms':medians,'overhead_ms':medians['recovering']-medians['native'],'samples_ms':timings}
print(json.dumps(results,indent=2))
