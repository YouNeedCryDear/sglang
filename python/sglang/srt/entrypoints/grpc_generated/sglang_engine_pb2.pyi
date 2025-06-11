from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar
from typing import Optional as _Optional

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class GenerateRequest(_message.Message):
    __slots__ = ("request_json_body", "headers")

    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    REQUEST_JSON_BODY_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    request_json_body: str
    headers: _containers.ScalarMap[str, str]
    def __init__(
        self,
        request_json_body: _Optional[str] = ...,
        headers: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class GenerateResponse(_message.Message):
    __slots__ = ("response_json_body", "status_code")
    RESPONSE_JSON_BODY_FIELD_NUMBER: _ClassVar[int]
    STATUS_CODE_FIELD_NUMBER: _ClassVar[int]
    response_json_body: str
    status_code: int
    def __init__(
        self,
        response_json_body: _Optional[str] = ...,
        status_code: _Optional[int] = ...,
    ) -> None: ...

class TokenUpdate(_message.Message):
    __slots__ = ("json_chunk",)
    JSON_CHUNK_FIELD_NUMBER: _ClassVar[int]
    json_chunk: str
    def __init__(self, json_chunk: _Optional[str] = ...) -> None: ...
