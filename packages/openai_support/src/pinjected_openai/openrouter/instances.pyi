from typing import overload
from pydantic import BaseModel
from pinjected import IProxy

# IMPORTANT: @injected functions MUST use @overload in .pyi files
# The @overload decorator is required to properly type-hint the user-facing interface
# This allows IDEs to show only runtime arguments (after /) to users
# DO NOT change @overload to @injected - this is intentional for IDE support

@overload
async def a_sllm_openrouter(
    text: str,
    model: str,
    images=...,
    response_format: type[BaseModel] | None = ...,
    max_tokens: int = ...,
): ...

# Additional symbols:
a_cached_structured_llm__gemini_flash_2_0: IProxy[StructuredLLM]
a_cached_structured_llm__deepseek_chat: IProxy[StructuredLLM]
a_cached_structured_llm__gemini_flash_thinking_2_0: IProxy[StructuredLLM]
a_cached_structured_llm__claude_sonnet_3_5: IProxy[StructuredLLM]
a_cached_sllm_gpt4o__openrouter: IProxy
a_cached_sllm_gpt4o_mini__openrouter: IProxy
test_cached_sllm_gpt4o_mini: IProxy
test_cached_sllm_gpt4o: IProxy
test_gemini_flash_2_0_structured: IProxy

class StructuredLLM: ...
class NoEndpointsFoundError: ...

# Additional symbols:
class ASllmOpenrouterProtocol: ...
