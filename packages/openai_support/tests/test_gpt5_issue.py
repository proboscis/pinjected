"""Test to reproduce GPT-5 issue with response_format."""

import pytest
from pinjected import IProxy
from pinjected.test import injected_pytest
from pinjected_openai.openrouter.util import a_openrouter_chat_completion
from pydantic import BaseModel
from loguru import logger


class A(BaseModel):
    random_text: str


@pytest.mark.asyncio
@injected_pytest
async def test_gpt5_response_format(
    a_openrouter_chat_completion,
    openrouter_model_table,
    logger,
    /,
):
    """Test GPT-5 with response_format."""

    # First check if GPT-5 supports JSON
    model = openrouter_model_table.get_model("openai/gpt-5")
    if model:
        logger.info(f"GPT-5 found in model table")
        logger.info(f"Supported parameters: {model.supported_parameters}")
        logger.info(f"Supports JSON: {model.supports_json_output()}")
    else:
        logger.warning("GPT-5 not found in model table")

    # Try to use it with response_format
    try:
        result = await a_openrouter_chat_completion(
            prompt="hello, respond with some random text",
            model="openai/gpt-5",
            response_format=A,
            max_tokens=100,
        )
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result: {result}")
        assert isinstance(result, A)
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


@pytest.mark.asyncio
@injected_pytest
async def test_gpt5_direct_proxy():
    """Test GPT-5 with direct IProxy definition."""
    from pinjected import Injected

    # This simulates the user's code
    check_gpt5: IProxy = a_openrouter_chat_completion(
        prompt="hello",
        model="openai/gpt-5",
        response_format=A,
    )

    # Try to evaluate it
    try:
        result = await Injected.wrap(check_gpt5).eval()
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"Direct proxy error: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
