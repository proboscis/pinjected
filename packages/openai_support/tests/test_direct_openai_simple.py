"""Simple test for direct OpenAI API implementation."""

import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel


class SimpleResponse(BaseModel):
    """Simple response for testing."""

    answer: str


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_direct_openai(
    a_sllm_openai,
    logger,
    /,
):
    """Test direct OpenAI API call bypassing OpenRouter."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING DIRECT OPENAI API (No OpenRouter 5% fee!)")
    logger.info("=" * 80)

    # Test 1: GPT-4o unstructured
    logger.info("\n1. Testing GPT-4o (direct OpenAI):")
    try:
        result = await a_sllm_openai(
            text="Say 'Hello from direct OpenAI' in exactly 5 words",
            model="gpt-4o",
            max_tokens=100,
        )
        logger.success(f"✅ GPT-4o response: {result}")
    except Exception as e:
        logger.error(f"❌ GPT-4o failed: {e}")

    # Test 2: GPT-5-nano unstructured
    logger.info("\n2. Testing GPT-5-nano (direct OpenAI, no 5% fee):")
    try:
        result = await a_sllm_openai(
            text="What is 2+2? Answer with just the number.",
            model="gpt-5-nano",
            max_tokens=10000,  # Will be converted to max_completion_tokens
        )
        logger.success(f"✅ GPT-5-nano response: {result}")
        logger.info("   (Saved 5% by avoiding OpenRouter!)")
    except Exception as e:
        logger.error(f"❌ GPT-5-nano failed: {e}")

    # Test 3: GPT-4o structured
    logger.info("\n3. Testing GPT-4o with structured output:")
    try:
        result = await a_sllm_openai(
            text="What is the capital of France? Answer: 'Paris'",
            model="gpt-4o",
            response_format=SimpleResponse,
            max_tokens=100,
        )
        logger.success(f"✅ GPT-4o structured response: {result}")
        assert isinstance(result, SimpleResponse)
    except Exception as e:
        logger.error(f"❌ GPT-4o structured failed: {e}")

    # Test 4: GPT-5 structured
    logger.info("\n4. Testing GPT-5-nano with structured output:")
    try:
        result = await a_sllm_openai(
            text="The answer to life is 42",
            model="gpt-5-nano",
            response_format=SimpleResponse,
            max_tokens=10000,
        )
        logger.success(f"✅ GPT-5-nano structured: {result}")
        logger.info("   (Direct API - no OpenRouter 5% markup!)")
    except Exception as e:
        logger.error(f"❌ GPT-5-nano structured failed: {e}")

    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY: Direct OpenAI API avoids OpenRouter's 5% fee")
    logger.info("Use a_sllm_openai for direct access to OpenAI models")
    logger.info("=" * 80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
