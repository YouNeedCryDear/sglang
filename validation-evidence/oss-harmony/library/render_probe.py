import json
from pathlib import Path
from openai_harmony import *
enc=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
user=Message.from_role_and_content(Role.USER,'What is the weather in Paris?')
system=Message.from_role_and_content(Role.SYSTEM,SystemContent.new().with_conversation_start_date('2026-11-03'))
dev=Message.from_role_and_content(Role.DEVELOPER,DeveloperContent.new().with_instructions('Be concise.').with_function_tools([ToolDescription.new(name='weather',description='Get weather',parameters={'type':'object','properties':{'city':{'type':'string'}}})]))
cases={
 'plain': [system,user],
 'tools': [system,dev,user],
 'analysis': [system,user,Message.from_role_and_content(Role.ASSISTANT,'I should check.').with_channel('analysis')],
 'final': [system,user,Message.from_role_and_content(Role.ASSISTANT,'It is sunny.').with_channel('final')],
 'commentary': [system,user,Message.from_role_and_content(Role.ASSISTANT,'Checking now.').with_channel('commentary')],
 'tool_call': [system,dev,user,Message.from_role_and_content(Role.ASSISTANT,'{"city":"Paris"}').with_channel('commentary').with_recipient('functions.weather')],
 'tool_call_json': [system,dev,user,Message.from_role_and_content(Role.ASSISTANT,'{"city":"Paris"}').with_channel('commentary').with_recipient('functions.weather').with_content_type('json')],
 'python': [system,user,Message.from_role_and_content(Role.ASSISTANT,'print(1 + 1)').with_channel('analysis').with_recipient('python')],
 'python_code': [system,user,Message.from_role_and_content(Role.ASSISTANT,'print(1 + 1)').with_channel('analysis').with_recipient('python').with_content_type('code')],
 'browser_json': [system,user,Message.from_role_and_content(Role.ASSISTANT,'{"query":"weather"}').with_channel('analysis').with_recipient('browser.search').with_content_type('json')],
 'browser': [system,user,Message.from_role_and_content(Role.ASSISTANT,'{"query":"weather"}').with_channel('analysis').with_recipient('browser.search')],
}
out={}
for name,msgs in cases.items():
 tokens=enc.render_conversation_for_completion(Conversation.from_messages(msgs),Role.ASSISTANT)
 out[name]={'tokens':tokens,'text':enc.decode(tokens)}
print(json.dumps(out,indent=2))
