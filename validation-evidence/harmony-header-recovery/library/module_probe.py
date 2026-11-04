import importlib.util
import json
from pathlib import Path
from openai_harmony import HarmonyEncodingName, HarmonyError, Role, StreamableParser, load_harmony_encoding

source=Path(__file__).resolve().parents[3] / 'python/sglang/srt/entrypoints/harmony_recovery.py'
spec=importlib.util.spec_from_file_location('harmony_recovery',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
encoding=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)

def encode(text): return encoding.encode(text,allowed_special='all')
def parse(tokens, repaired=True, names={'echo'}, role=Role.ASSISTANT):
    parser=module.RecoveringHarmonyParser(encoding,function_names=names,role=role) if repaired else StreamableParser(encoding,role=role)
    for token in tokens: parser.process(token)
    if repaired: parser.finish()
    return parser

def messages(parser): return [message.to_dict() for message in parser.messages]

out={}
valid=[
 '<|channel|>analysis<|message|>Think.<|end|><|start|>assistant<|channel|>final<|message|>Done.<|return|>',
 '<|channel|>commentary to=functions.echo <|constrain|>json<|message|>{"x":1}<|call|>',
 ' to=python<|channel|>analysis<|message|>print(1)<|call|>',
 '<|channel|>final<|message|>unfinished',
]
for index,text in enumerate(valid):
    tokens=encode(text); baseline=parse(tokens,False); candidate=parse(tokens)
    assert messages(candidate)==messages(baseline)
    assert candidate.tokens==baseline.tokens
    assert candidate.state==baseline.state
    assert candidate.current_content==baseline.current_content
out['valid_unchanged']=len(valid)

metadata=[
 '<|channel|>commentary to=python <|constrain|>commentary to=assistant<|constrain|>analysis to=python code<|message|>print(1)<|call|>',
 ' to=python<|channel|>analysis <|constrain|>analysis to=python code<|message|>print(1)<|call|>',
 '<|channel|>commentary to=functions.echo <|constrain|><|channel|><|constrain|>json<|message|>{"x":1}<|call|>',
]
for text in metadata:
    tokens=encode(text)
    try: parse(tokens,False)
    except HarmonyError: pass
    else: raise AssertionError('baseline unexpectedly accepted malformed metadata')
    parser=parse(tokens); assert len(parser.messages)==1
out['metadata_recovered']=len(metadata)

for text in ['<|channel|>commentary to=python <|constrain|>analysis authored code<|message|>', '<|channel|>commentary to=python <|constrain|>analysis text<|message|>', '<|channel|>commentary to=python <|constrain|>analysis<|call|> code<|message|>']:
    try: parse(encode(text))
    except HarmonyError: pass
    else: raise AssertionError('unrecognized metadata did not retain error')
out['metadata_rejected']=3

arguments=' {"x":"literal <|call|> and café"}'
argument_tokens=[token for char in arguments for token in encoding.encode(char,disallowed_special=())]
for channel in ('analysis','commentary'):
    for constrain in ('',' <|constrain|>'):
        tokens=encode(f'<|channel|>{channel} to=functions.echo{constrain}')+argument_tokens+encode('<|call|>')
        parser=parse(tokens)
        assert len(parser.messages)==1
        assert parser.messages[0].content[0].text==arguments
        message=encode('<|message|>')[0]
        assert parser.tokens[parser.tokens.index(message)+1:-1]==argument_tokens
out['missing_message_recovered_preserving_argument_ids']=4

invalid=[
 '<|channel|>commentary to=functions.unknown {"x":1}<|call|>',
 '<|channel|>commentary to=functions.echo {"x":NaN}<|call|>',
 '<|channel|>commentary to=functions.echo {"x":Infinity}<|call|>',
 '<|channel|>commentary to=functions.echo {"x":1}',
 '<|channel|>commentary to=functions.echo {"x":1<|call|>',
 '<|channel|>commentary to=functions.echo {"x":1} prose<|call|>',
 '<|channel|>commentary to=functions.echo []<|call|>',
 '<|channel|>final to=functions.echo {"x":1}<|call|>',
 '<|channel|>commentary to=python {"x":1}<|call|>',
 '<|channel|>commentary to=functions.echo <|constrain|>json {"x":1}<|call|>',
 '<|channel|>commentary to=functions.echo {"x":"<|call|>"}<|call|>',
]
for text in invalid:
    parser=parse(encode(text)); assert not parser.messages,text
out['missing_message_rejected']=len(invalid)

prefix=encode('<|channel|>analysis<|message|>Think.<|end|>')
first=encode('<|start|>assistant<|channel|>commentary to=python <|constrain|>analysis code<|message|>print(1)<|call|>')
second=encode('<|start|>assistant<|channel|>commentary to=functions.echo {"x":1}<|call|>')
parser=parse(prefix+first+second)
assert len(parser.messages)==3
assert [m.content[0].text for m in parser.messages]==['Think.','print(1)',' {"x":1}']
assert parser.tokens[:len(prefix)]==prefix
out['prior_messages_once_across_two_repairs']=3

# Repeated completion checks and later tool/assistant continuation remain valid.
parser.finish(); assert len(parser.messages)==3
continuation=encode('<|start|>tool<|message|>ok<|end|><|start|>assistant<|channel|>final<|message|>Done<|return|>')
for token in continuation: parser.process(token)
parser.finish(); assert len(parser.messages)==5
out['messages_after_valid_continuation']=5
print(json.dumps(out,indent=2))
