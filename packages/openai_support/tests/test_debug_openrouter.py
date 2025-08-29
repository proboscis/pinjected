"""Debug test to understand what's being returned."""

from packages.openai_support.conftest import apikey_skip_if_needed
import pytest
from pinjected.test import injected_pytest
from pydantic import BaseModel
from loguru import logger

apikey_skip_if_needed()


class SimpleModel(BaseModel):
    """Simple model for testing."""

    name: str
    age: int


@pytest.mark.asyncio
@injected_pytest
async def test_debug_base_completion(
    a_openrouter_base_chat_completion,
    openrouter_api,
    /,
):
    """Debug what base completion returns."""
    result = await a_openrouter_base_chat_completion(
        prompt="Create a JSON object with name='John' and age=30",
        model="openai/gpt-4o-mini",
        max_tokens=100,
        temperature=0,
    )

    logger.info(f"Base result type: {type(result)}")
    logger.info(f"Base result: {result!r}")

    assert isinstance(result, str)


@pytest.mark.asyncio
@injected_pytest
async def test_debug_with_response_format(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Debug what happens with response_format."""
    result = await a_openrouter_chat_completion(
        prompt="Create a person named John who is 30 years old.",
        model="openai/gpt-4o-mini",
        max_tokens=100,
        temperature=0,
        response_format=SimpleModel,
    )

    logger.info(f"Result type: {type(result)}")
    logger.info(f"Result: {result!r}")

    # This should be SimpleModel, not str
    if isinstance(result, str):
        logger.error(f"Got string instead of SimpleModel: {result}")

    assert isinstance(result, SimpleModel)
    assert result.name == "John"
    assert result.age == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
