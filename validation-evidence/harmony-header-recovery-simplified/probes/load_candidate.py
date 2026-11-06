"""AST-extract actual helpers/context classes with real Harmony bindings.

This avoids unrelated SGLang server/GPU imports and is not a full-runtime test.
"""
import ast
import argparse
import hashlib
import subprocess
import re
from abc import ABC, abstractmethod
from collections.abc import Collection
from pathlib import Path
from typing import Union
import orjson
import openai_harmony

arguments=argparse.ArgumentParser(description=__doc__)
arguments.add_argument('source_root', type=Path, help='SGLang source checkout')
SOURCE_ROOT=arguments.parse_args().source_root.resolve()
utils_path=SOURCE_ROOT/'python/sglang/srt/entrypoints/harmony_utils.py'
context_path=SOURCE_ROOT/'python/sglang/srt/entrypoints/context.py'
namespace={name:getattr(openai_harmony,name) for name in dir(openai_harmony)}
namespace.update(re=re,orjson=orjson,Collection=Collection,Union=Union,ABC=ABC,abstractmethod=abstractmethod,Tool=type('UnusedTool',(),{}),_harmony_encoding=None)
functions={'get_encoding','get_streamable_parser_for_assistant','render_for_completion','_harmony_token_id','_current_harmony_header','_is_assistant_harmony_prefix','_replay_harmony_tokens','recover_harmony_header','_harmony_argument_tokens','recover_harmony_missing_message'}
tree=ast.Module(body=[node for node in ast.parse(utils_path.read_text()).body if isinstance(node,ast.FunctionDef) and node.name in functions],type_ignores=[])
exec(compile(tree,str(utils_path),'exec'),namespace)
tree=ast.Module(body=[node for node in ast.parse(context_path.read_text()).body if isinstance(node,ast.ClassDef) and node.name in {'ConversationContext','HarmonyContext','StreamingHarmonyContext'}],type_ignores=[])
exec(compile(tree,str(context_path),'exec'),namespace)
HarmonyContext=namespace['HarmonyContext']
StreamingHarmonyContext=namespace['StreamingHarmonyContext']
encoding=namespace['get_encoding']()


def source_metadata():
    return {
        'validation_kind':'isolated AST-extracted actual helpers/context classes; real Harmony library; not full runtime',
        'commit':subprocess.check_output(['git','-C',str(SOURCE_ROOT),'rev-parse','HEAD'],text=True).strip(),
        'sha256':{str(path.relative_to(SOURCE_ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (utils_path,context_path)},
    }
