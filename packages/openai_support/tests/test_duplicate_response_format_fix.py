"""Test to verify the duplicate response_format parameter fix."""

import pytest
from pinjected.test import injected_pytest
from pydantic import BaseModel


class SimpleResponse(BaseModel):
    message: str


@pytest.mark.asyncio
@injected_pytest
async def test_no_duplicate_response_format(
    a_openrouter_chat_completion,
    openrouter_model_table,
    logger,
    /,
):
    """Test that response_format is not passed twice to base completion.

    This test verifies the fix for the bug where response_format was being
    passed both explicitly (as None) and in **kwargs when the model supports JSON.
    """

    # Test with a model that supports JSON
    model = openrouter_model_table.get_model("openai/gpt-4o-mini")
    if model:
        logger.info(f"Model supports JSON: {model.supports_json_output()}")

    # This should work without TypeError about duplicate keyword argument
    result = await a_openrouter_chat_completion(
        prompt="Say hello",
        model="openai/gpt-4o-mini",
        response_format=SimpleResponse,
        max_tokens=50,
        temperature=0,
    )

    logger.info(f"Result: {result}")
    assert isinstance(result, SimpleResponse)
    assert result.message


@pytest.mark.asyncio
@injected_pytest
async def test_models_with_supported_parameters(
    a_openrouter_chat_completion,
    openrouter_model_table,
    logger,
    /,
):
    """Test models that have supported_parameters field with response_format."""

    # Find a model with supported_parameters containing response_format
    test_model = None
    for model in openrouter_model_table.data:
        if (
            model.supported_parameters
            and "response_format" in model.supported_parameters
        ):
            test_model = model.id
            logger.info(f"Testing with model: {model.id}")
            break

    if not test_model:
        pytest.skip("No models with supported_parameters containing response_format")

    # This should work without duplicate parameter error
    try:
        result = await a_openrouter_chat_completion(
            prompt="Say hello",
            model=test_model,
            response_format=SimpleResponse,
            max_tokens=50,
            temperature=0,
        )
        logger.info(f"Success with {test_model}: {result}")
        assert isinstance(result, SimpleResponse)
    except Exception as e:
        # Some models might require BYOK or have other restrictions
        if "404" in str(e) or "No endpoints" in str(e):
            logger.info(f"Model {test_model} requires BYOK setup")
            pytest.skip(f"Model {test_model} requires BYOK")
        else:
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
