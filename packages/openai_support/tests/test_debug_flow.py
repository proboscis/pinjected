"""Debug the flow with response_format."""

import pytest
from pinjected.test import injected_pytest
from pydantic import BaseModel


class SimpleModel(BaseModel):
    """Simple model for testing."""

    name: str
    age: int


@pytest.mark.asyncio
@injected_pytest
async def test_debug_flow_with_logging(
    a_openrouter_chat_completion,
    openrouter_api,
    logger,
    /,
):
    """Debug the flow to see where it's failing."""

    # Check what type response_format is
    response_format = SimpleModel
    logger.info(f"response_format type: {type(response_format)}")
    logger.info(f"response_format value: {response_format}")
    logger.info(f"Is None? {response_format is None}")
    logger.info(f"Is subclass of BaseModel? {issubclass(response_format, BaseModel)}")

    # Call the function with explicit logging
    logger.info("Calling a_openrouter_chat_completion with response_format=SimpleModel")

    result = await a_openrouter_chat_completion(
        prompt="Create a person named John who is 30 years old.",
        model="openai/gpt-4o-mini",
        max_tokens=100,
        temperature=0,
        response_format=response_format,
    )

    logger.info(f"Result type: {type(result)}")
    logger.info(f"Result value: {result!r}")

    # This should be SimpleModel
    assert isinstance(result, SimpleModel), (
        f"Expected SimpleModel, got {type(result)}: {result}"
    )
    assert result.name == "John"
    assert result.age == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
