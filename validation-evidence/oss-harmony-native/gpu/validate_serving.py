import argparse, json, time, pathlib, sys, importlib.metadata, platform, subprocess
import requests
p=argparse.ArgumentParser(); p.add_argument('phase'); args=p.parse_args()
out=pathlib.Path('/work')/args.phase; out.mkdir(exist_ok=True)
base='http://127.0.0.1:30071'
for _ in range(180):
    try:
        if requests.get(base+'/health',timeout=3).status_code == 200: break
    except requests.RequestException: pass
    time.sleep(5)
else: raise RuntimeError('server not ready after 15 minutes')
def get_version(name):
    try:return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:return None
versions={x:get_version(x) for x in ['sglang','torch','openai','openai-harmony','oss-harmony','transformers','triton','triton-kernels','flashinfer-python','sgl-kernel','sglang-kernel','tml-renderers','pytest','pytest-asyncio']}
versions['python']=platform.python_version(); versions['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],text=True).strip()
(out/'versions.json').write_text(json.dumps(versions,indent=2))
(out/'server_info.json').write_text(json.dumps(requests.get(base+'/get_server_info',timeout=10).json(),indent=2))
model='gpt-oss-20b'
tool={'type':'function','name':'get_weather','description':'Get the current weather for a city.','parameters':{'type':'object','properties':{'city':{'type':'string'}},'required':['city'],'additionalProperties':False},'strict':True}
common={'model':model,'temperature':0,'max_output_tokens':512,'reasoning':{'effort':'low'},'store':False}
cases=[]
for name,prompt,expect in [('arithmetic','What is 17 plus 25? Answer with the number only.','42'),('capital','What is the capital of France? Answer with the city name only.','Paris'),('literal','Reply with exactly the word BLUE and nothing else.','BLUE')]:
    for stream in [False,True]: cases.append((name+('_stream' if stream else ''),'/v1/responses',{**common,'input':prompt,'stream':stream},'text',expect))
for stream in [False,True]:
    cases.append(('tool_call'+('_stream' if stream else ''),'/v1/responses',{**common,'input':'Use get_weather to look up the current weather in Paris. Call the tool before answering.','tools':[tool],'tool_choice':'auto','stream':stream},'tool','Paris'))
replay=[{'role':'user','content':'What is the current weather in Paris?'},{'type':'function_call','call_id':'call_weather_fixed','name':'get_weather','arguments':'{"city":"Paris"}'},{'type':'function_call_output','call_id':'call_weather_fixed','output':'{"city":"Paris","temperature_c":21,"conditions":"sunny"}'}]
for stream in [False,True]:
    cases.append(('tool_replay'+('_stream' if stream else ''),'/v1/responses',{**common,'input':replay,'instructions':'Use the tool result and answer in one short sentence.','tools':[tool],'stream':stream},'replay','21'))
for stream in [False,True]:
    cases.append(('chat_control'+('_stream' if stream else ''),'/v1/chat/completions',{'model':model,'messages':[{'role':'user','content':'What is 17 plus 25? Answer with the number only.'}],'temperature':0,'max_tokens':512,'reasoning_effort':'low','stream':stream},'chat','42'))
history=[
    {'role':'user','content':'What is the current weather in Paris?'},
    {'type':'function_call','call_id':'call_paris_fixed','name':'get_weather','arguments':'{"city":"Paris"}'},
    {'type':'function_call_output','call_id':'call_paris_fixed','output':'{"city":"Paris","temperature_c":21,"conditions":"sunny"}'},
    {'role':'assistant','content':'Paris is 21 C and sunny.'},
    {'role':'user','content':'And what is the current weather in London?'},
    {'type':'function_call','call_id':'call_london_fixed','name':'get_weather','arguments':'{"city":"London"}'},
    {'type':'function_call_output','call_id':'call_london_fixed','output':'{"city":"London","temperature_c":11,"conditions":"cloudy"}'},
    {'role':'assistant','content':'London is 11 C and cloudy.'},
    {'role':'user','content':'Now use get_weather to look up the current weather in Rome. Call the tool before answering.'},
]
rome_result=[
    {'type':'function_call','call_id':'call_rome_fixed','name':'get_weather','arguments':'{"city":"Rome"}'},
    {'type':'function_call_output','call_id':'call_rome_fixed','output':'{"city":"Rome","temperature_c":25,"conditions":"clear"}'},
]
for stream in [False,True]:
    cases.append(('multiturn_next_call'+('_stream' if stream else ''),'/v1/responses',{**common,'input':history,'tools':[tool],'tool_choice':'auto','stream':stream},'tool','Rome'))
    cases.append(('multiturn_replay'+('_stream' if stream else ''),'/v1/responses',{**common,'input':history+rome_result,'instructions':'Use the latest tool result to answer the latest question in one short sentence.','tools':[tool],'stream':stream},'multi_replay','25'))
summary=[]
def extract_text(response):
    return ''.join(c.get('text','') for item in response.get('output',[]) if item.get('type')=='message' for c in item.get('content',[]) if c.get('type')=='output_text')
def canonical(value):
    if isinstance(value,list):return [canonical(x) for x in value]
    if isinstance(value,dict):return {k:canonical(v) for k,v in value.items() if k not in {'id','call_id','created','created_at','completed_at','system_fingerprint','request_id','cached_tokens'}}
    return value
for name,path,body,kind,expect in cases:
    record={'name':name,'path':path,'request':body}; started=time.perf_counter()
    try:
        response=requests.post(base+path,json=body,timeout=240,stream=body.get('stream',False)); record['status_code']=response.status_code
        if not response.ok:
            record['error']=response.text; response.raise_for_status()
        if body.get('stream'):
            events=[]
            for line in response.iter_lines():
                if line.startswith(b'data: '):
                    data=line[6:]
                    if data!=b'[DONE]':events.append(json.loads(data))
            record['events']=events
            if kind=='chat':
                text=''.join(e['choices'][0].get('delta',{}).get('content') or '' for e in events if e.get('choices'))
                reasoning=''.join(e['choices'][0].get('delta',{}).get('reasoning_content') or '' for e in events if e.get('choices'))
                result={'text':text,'reasoning_content':reasoning}
            else:
                finals=[e['response'] for e in events if e.get('type') in {'response.completed','response.incomplete'}]
                assert finals, 'missing terminal response event'
                record['response']=finals[-1]; result=finals[-1]
                assert result['status']=='completed',result['status']
                text=extract_text(result)
        else:
            result=response.json(); record['response']=result
            text=result['choices'][0]['message']['content'] if kind=='chat' else extract_text(result)
            if kind!='chat':assert result['status']=='completed',result.get('status')
        if kind=='tool':
            calls=[x for x in result.get('output',[]) if x.get('type')=='function_call']
            assert len(calls)==1,calls
            assert calls[0]['name']=='get_weather',calls[0]
            assert json.loads(calls[0]['arguments'])=={'city':expect},calls[0]
        else:
            assert expect.lower() in (text or '').lower(),repr(text)
            if kind=='replay':assert 'sunny' in text.lower(),text
            if kind=='multi_replay':assert 'rome' in text.lower() and 'clear' in text.lower(),text
        record['passed']=True;record['text']=text; record['canonical']=canonical(result)
    except Exception as exc:
        record['passed']=False;record['exception']=repr(exc)
    record['elapsed_seconds']=round(time.perf_counter()-started,3)
    (out/(name+'.json')).write_text(json.dumps(record,indent=2))
    summary.append({k:record.get(k) for k in ['name','status_code','passed','text','exception','elapsed_seconds']})
    print(json.dumps(summary[-1]),flush=True)
(out/'summary.json').write_text(json.dumps(summary,indent=2))
print(f"TOTAL {sum(x['passed'] for x in summary)}/{len(summary)} passed",flush=True)
if not all(x['passed'] for x in summary):sys.exit(1)
