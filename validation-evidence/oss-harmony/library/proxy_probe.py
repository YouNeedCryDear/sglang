import json,os,socket,subprocess,sys,tempfile
with tempfile.TemporaryDirectory() as cache_dir, socket.socket() as proxy:
 proxy.bind(('127.0.0.1',0))
 proxy_url=f'http://127.0.0.1:{proxy.getsockname()[1]}'
 env=os.environ.copy();env.pop('TIKTOKEN_ENCODINGS_BASE',None)
 env.update(TIKTOKEN_RS_CACHE_DIR=cache_dir,TIKTOKEN_CACHE_DIR=cache_dir)
 for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY'):
  env[name]=env[name.lower()]=proxy_url
 env['NO_PROXY']=env['no_proxy']=''
 result=subprocess.run([sys.executable,'-c','from openai_harmony import *; enc=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS); assert enc.decode(enc.encode("Hello")) == "Hello"'],env=env,capture_output=True,text=True,timeout=30)
 print(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}))
