"""Simple test to verify JSON response_format works."""

import pytest
from pinjected.test import injected_pytest
from pydantic import BaseModel
from loguru import logger
from packages.openai_support.conftest import apikey_skip_if_needed

apikey_skip_if_needed()


class SimpleResponseModel(BaseModel):
    """Simple response model."""

    name: str
    value: int


@pytest.mark.asyncio
@injected_pytest
async def test_json_response(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test JSON response."""

    result = await a_openrouter_chat_completion(
        prompt='Return JSON with name="test" and value=42',
        model="openai/gpt-4o-mini",
        max_tokens=50,
        temperature=0,
        response_format=SimpleResponseModel,
    )

    logger.info(f"Result type: {type(result)}")
    logger.info(f"Result: {result}")

    assert isinstance(result, SimpleResponseModel)
    assert result.name == "test"
    assert result.value == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
