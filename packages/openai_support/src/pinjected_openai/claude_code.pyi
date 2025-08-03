from typing import Any, Protocol, overload
from pinjected import IProxy
from pydantic import BaseModel

claude_command_path_str: IProxy[str]

class ClaudeCommandPathStrProtocol(Protocol):
    def __call__(self) -> str: ...

class ClaudeCodeError(Exception):
    ...

class ClaudeCodeTimeoutError(ClaudeCodeError):
    ...

class ClaudeCodeNotFoundError(ClaudeCodeError):
    ...

class StructuredLLM(Protocol):
    async def __call__(self, text: str, images = ..., response_format: type[BaseModel] | None = ...) -> Any: ...

class ClaudeCodeSubprocessProtocol(Protocol):
    async def __call__(self, prompt: str, timeout: float = ..., **kwargs) -> str: ...

class ClaudeCodeStructuredProtocol(Protocol):
    async def __call__(self, prompt: str, response_format: type[BaseModel], **kwargs) -> BaseModel: ...

class SimpleResponse(BaseModel):
    answer: str
    confidence: float

@overload
async def a_claude_code_subprocess(prompt: str, timeout: float = ..., **kwargs) -> IProxy[str]: ...

@overload
async def a_claude_code_structured(prompt: str, response_format: type[BaseModel], **kwargs) -> IProxy[BaseModel]: ...

@overload
async def a_sllm_claude_code(text: str, images = ..., response_format: type[BaseModel] | None = ..., max_tokens: int = ...) -> IProxy[Any]: ...

test_claude_code_plain: IProxy

test_claude_code_structured: IProxy

a_cached_sllm_claude_code: IProxy[StructuredLLM]

@overload
def claude_command_path_str() -> IProxy[str]: ...
