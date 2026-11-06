"""CPU-only native versus actual context methods, with recovery measured separately."""
import importlib.metadata
import json
import statistics
import time
from openai_harmony import Role, StreamableParser
from load_candidate import HarmonyContext, encoding, source_metadata


def encode(text):
    return encoding.encode(text, allowed_special='all')


def summarize(samples):
    return {'median_ms':statistics.median(samples),'samples_ms':samples}


results={'source':source_metadata(),'repeats':10,'units':'milliseconds','valid_processing':{},'failure_recovery':{}}
for package in ('openai-harmony','oss-harmony'):
    try: results['distribution']={package:importlib.metadata.version(package)}
    except importlib.metadata.PackageNotFoundError: pass

body_token=encoding.encode(' hello',disallowed_special=())
assert len(body_token)==1
message_token=encode('<|message|>')[0]
for size in (1000,10000):
    tokens=encode('<|channel|>final<|message|>')+body_token*size+encode('<|return|>')
    timings={'native':[],'context':[]}
    for repeat in range(10):
        for name in (('native','context') if repeat%2==0 else ('context','native')):
            parser=StreamableParser(encoding,role=Role.ASSISTANT)
            context=HarmonyContext([],{},function_names={'echo'})
            process=parser.process if name=='native' else context._process_token
            start=time.perf_counter()
            for token in tokens: process(token)
            timings[name].append((time.perf_counter()-start)*1000)
            actual=parser if name=='native' else context.parser
            assert actual.tokens==tokens
            assert len(actual.messages)==1
            assert actual.messages[0].content[0].text==' hello'*size
    result={name:summarize(samples) for name,samples in timings.items()}
    result.update(body_tokens=size,total_tokens=len(tokens),overhead_ms=result['context']['median_ms']-result['native']['median_ms'])
    results['valid_processing'][str(size)]=result

for size in (0,1000,10000):
    history=(encode('<|channel|>analysis<|message|>')+body_token*size+encode('<|end|>')) if size else []
    lead=encode('<|start|>assistant') if history else []
    malformed=lead+encode('<|channel|>commentary to=functions.echo <|constrain|>analysis to=functions.echo json')
    missing=lead+encode('<|channel|>commentary to=functions.echo {"x":1}<|call|>')
    timings={'metadata_error':[],'missing_message_at_finish':[]}
    for repeat in range(10):
        for name in timings:
            context=HarmonyContext([],{},function_names={'echo'})
            for token in history+(malformed if name=='metadata_error' else missing):
                context.parser.process(token)
            start=time.perf_counter()
            if name=='metadata_error':
                context._process_token(message_token)
            else:
                context._finish_parser()
            timings[name].append((time.perf_counter()-start)*1000)
            if name=='metadata_error':
                for token in encode('{"x":1}<|call|>'): context.parser.process(token)
            assert len(context.parser.messages)==(2 if history else 1)
            assert context.parser.tokens[:len(history)]==history
            assert context.parser.messages[-1].recipient=='functions.echo'
    results['failure_recovery'][str(size)]={name:summarize(samples) for name,samples in timings.items()}
print(json.dumps(results,indent=2))
