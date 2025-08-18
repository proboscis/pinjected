"""Test to check what the API actually returns for model capabilities."""

import pytest
from pinjected.test import injected_pytest
from loguru import logger
import httpx
import json


@pytest.mark.asyncio
@injected_pytest
async def test_raw_api_response():
    """Check the raw API response for model capabilities."""

    async with httpx.AsyncClient() as client:
        response = await client.get("https://openrouter.ai/api/v1/models")
        response.raise_for_status()
        data = response.json()["data"]

        # Find gpt-4o-mini
        for model in data:
            if model["id"] == "openai/gpt-4o-mini":
                logger.info(f"Found openai/gpt-4o-mini:")
                logger.info(f"Full model data: {json.dumps(model, indent=2)}")

                if "architecture" in model:
                    arch = model["architecture"]
                    logger.info(f"Architecture: {json.dumps(arch, indent=2)}")

                    if "capabilities" in arch:
                        caps = arch["capabilities"]
                        logger.info(f"Capabilities: {json.dumps(caps, indent=2)}")
                        logger.info(f"Has 'json' field: {'json' in caps}")
                        if "json" in caps:
                            logger.info(f"JSON value: {caps['json']}")
                break
        else:
            logger.error("openai/gpt-4o-mini not found in API response")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
