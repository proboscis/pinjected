"""Debug what parameters are being sent in the payload."""

import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest


@pytest.mark.asyncio
@injected_pytest(design(openrouter_api_key=injected("openrouter_api_key__personal")))
async def test_debug_payload_transformation(
    openrouter_model_table,
    logger,
    /,
):
    """Check what parameters the model table says GPT-5 supports."""

    # Check GPT-5 model info
    models_to_check = ["openai/gpt-5", "openai/gpt-5-nano", "openai/gpt-4o"]

    for model_name in models_to_check:
        model = openrouter_model_table.get_model(model_name)
        if model:
            logger.info(f"\n{model_name}:")
            logger.info(f"  Supported parameters: {model.supported_parameters}")
            if model.supported_parameters:
                supports_max_tokens = "max_tokens" in model.supported_parameters
                supports_max_completion_tokens = (
                    "max_completion_tokens" in model.supported_parameters
                )
                logger.info(f"  Supports max_tokens: {supports_max_tokens}")
                logger.info(
                    f"  Supports max_completion_tokens: {supports_max_completion_tokens}"
                )
        else:
            logger.warning(f"Model {model_name} not found in table")


@pytest.mark.asyncio
@injected_pytest
async def test_intercept_actual_payload(
    logger,
    /,
):
    """Test what's actually being sent to OpenRouter."""
    import json

    # Mock the actual request to see what's being sent
    class InterceptClient:
        def __init__(self, logger):
            self.logger = logger

        async def post(self, url, headers, json_data, timeout):
            self.logger.info(f"URL: {url}")
            self.logger.info(f"Payload being sent:")
            self.logger.info(json.dumps(json_data, indent=2))

            # Return a mock response
            class MockResponse:
                status_code = 200

                def json(self):
                    return {"choices": [{"message": {"content": "Mock response"}}]}

            return MockResponse()

    # We'd need to patch httpx.AsyncClient to actually intercept
    # For now, just log what we expect
    logger.info(
        "To properly debug, we need to patch httpx.AsyncClient in a_openrouter_post"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
