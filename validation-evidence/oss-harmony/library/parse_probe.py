import json
from pathlib import Path
from openai_harmony import HarmonyEncodingName, Role, StreamableParser, load_harmony_encoding
enc=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
fixtures=json.loads(Path(__file__).with_name('before.json').read_text())
out={}
for name,case in fixtures.items():
 tokens=case['tokens']
 # Completion prefix is an intentionally open next assistant header.
 end=enc.encode('<|start|>assistant',allowed_special='all')
 assert tokens[-len(end):]==end
 tokens=tokens[:-len(end)]
 parsed=enc.parse_messages_from_completion_tokens(tokens,role=None)
 parser=StreamableParser(enc,role=None)
 for token in tokens:
  parser.process(token)
 parser.process_eos()
 out[name]={'full':[m.to_dict() for m in parsed],'stream':[m.to_dict() for m in parser.messages]}
 assert out[name]['full']==out[name]['stream'],name
print(json.dumps(out,indent=2))
