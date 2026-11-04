import ctypes, errno, importlib.metadata, json, os, socket, tempfile
from pathlib import Path
import openai_harmony
# Deny socket creation at the syscall boundary, including the Rust extension.
seccomp=ctypes.CDLL('libseccomp.so.2',use_errno=True)
seccomp.seccomp_init.argtypes=[ctypes.c_uint32]
seccomp.seccomp_init.restype=ctypes.c_void_p
seccomp.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p]
seccomp.seccomp_syscall_resolve_name.restype=ctypes.c_int
seccomp.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
seccomp.seccomp_load.argtypes=[ctypes.c_void_p]
seccomp.seccomp_release.argtypes=[ctypes.c_void_p]
ctx=seccomp.seccomp_init(0x7fff0000)
assert ctx
assert seccomp.seccomp_rule_add(ctx,0x00050000|errno.EPERM,seccomp.seccomp_syscall_resolve_name(b'socket'),0)==0
assert seccomp.seccomp_load(ctx)==0
seccomp.seccomp_release(ctx)
try:
 socket.socket()
 raise AssertionError('Network guard not installed')
except PermissionError:
 pass
with tempfile.TemporaryDirectory() as cache:
 os.environ['TIKTOKEN_RS_CACHE_DIR']=cache
 os.environ['TIKTOKEN_CACHE_DIR']=cache
 os.environ.pop('TIKTOKEN_ENCODINGS_BASE',None)
 try:
  enc=openai_harmony.load_harmony_encoding(openai_harmony.HarmonyEncodingName.HARMONY_GPT_OSS)
  text='Offline Harmony: 你好, café.'
  tokens=enc.encode(text)
  assert enc.decode(tokens)==text
  print(json.dumps({'result':'PASS','network':'socket syscall denied EPERM','cache_files':list(Path(cache).iterdir()),'tokens':tokens}))
 except Exception as exc:
  print(json.dumps({'result':'FAIL','network':'socket syscall denied EPERM','error':str(exc),'cache_files':[str(p) for p in Path(cache).iterdir()]}))
  raise
