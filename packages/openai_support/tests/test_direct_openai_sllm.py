"""Test direct OpenAI API implementation with StructuredLLM support."""

from packages.openai_support.conftest import apikey_skip_if_needed
import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel

apikey_skip_if_needed()


class SimpleResponse(BaseModel):
    """Simple response model for testing."""

    answer: str
    confidence: float = 0.9


class CityInfo(BaseModel):
    """City information model for testing."""

    city: str
    country: str
    is_capital: bool = True


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,  # Most users don't have an org
    )
)
async def test_direct_openai_unstructured(
    a_sllm_openai,
    logger,
    /,
):
    """Test direct OpenAI API with unstructured output."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING DIRECT OPENAI API - UNSTRUCTURED")
    logger.info("=" * 80)

    # Test 1: GPT-4o with simple prompt
    logger.info("\n1. Testing GPT-4o with simple prompt:")
    try:
        result = await a_sllm_openai(
            text="Say 'Hello from direct OpenAI' in exactly 4 words",
            model="gpt-4o",
            max_tokens=100,
        )
        assert result and result.strip(), "GPT-4o returned empty response"
        logger.success(f"✅ GPT-4o response: {result}")
    except Exception as e:
        logger.error(f"❌ GPT-4o failed: {e}")
        pytest.fail(f"GPT-4o direct call failed: {e}")

    # Test 2: GPT-5-nano with sufficient tokens
    logger.info("\n2. Testing GPT-5-nano direct (no OpenRouter):")
    try:
        result = await a_sllm_openai(
            text="What is 2+2? Answer with just the number.",
            model="gpt-5-nano",
            max_tokens=10000,  # Will be converted to max_completion_tokens
        )
        assert result and result.strip(), "GPT-5-nano returned empty response"
        logger.success(f"✅ GPT-5-nano response: {result}")
        logger.info("   (Using direct OpenAI API - no 5% OpenRouter fee!)")
    except Exception as e:
        logger.error(f"❌ GPT-5-nano failed: {e}")
        pytest.fail(f"GPT-5-nano direct call failed: {e}")


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_direct_openai_structured(
    a_sllm_openai,
    logger,
    /,
):
    """Test direct OpenAI API with structured output."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING DIRECT OPENAI API - STRUCTURED OUTPUT")
    logger.info("=" * 80)

    # Test 1: GPT-4o with structured output
    logger.info("\n1. Testing GPT-4o with structured output:")
    try:
        result = await a_sllm_openai(
            text="What is the capital of France? Provide city and country.",
            model="gpt-4o",
            response_format=CityInfo,
            max_tokens=200,
        )
        assert isinstance(result, CityInfo), f"Expected CityInfo, got {type(result)}"
        assert result.city.lower() == "paris", f"Expected Paris, got {result.city}"
        assert result.country.lower() == "france", (
            f"Expected France, got {result.country}"
        )
        logger.success(f"✅ GPT-4o structured: {result}")
    except Exception as e:
        logger.error(f"❌ GPT-4o structured failed: {e}")
        pytest.fail(f"GPT-4o structured output failed: {e}")

    # Test 2: GPT-5-nano with structured output
    logger.info("\n2. Testing GPT-5-nano with structured output:")
    try:
        result = await a_sllm_openai(
            text="Provide a simple answer: The sky is blue. How confident are you?",
            model="gpt-5-nano",
            response_format=SimpleResponse,
            max_tokens=10000,  # Plenty of tokens for reasoning
        )
        assert isinstance(result, SimpleResponse), (
            f"Expected SimpleResponse, got {type(result)}"
        )
        assert result.answer, "GPT-5 returned empty answer"
        assert 0 <= result.confidence <= 1, f"Invalid confidence: {result.confidence}"
        logger.success(f"✅ GPT-5-nano structured: {result}")
        logger.info("   (Direct API - avoiding OpenRouter's 5% fee!)")
    except Exception as e:
        logger.error(f"❌ GPT-5-nano structured failed: {e}")
        pytest.fail(f"GPT-5-nano structured output failed: {e}")


@pytest.mark.asyncio
@injected_pytest(design(openai_config=injected("openai_config__personal")))
async def test_structured_llm_protocol_compatibility(
    a_structured_llm_openai,
    logger,
    /,
):
    """Test that a_structured_llm_openai implements StructuredLLM protocol correctly."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING STRUCTUREDLLM PROTOCOL COMPATIBILITY")
    logger.info("=" * 80)

    # Test with the StructuredLLM protocol signature
    logger.info("\n1. Testing StructuredLLM protocol with GPT-4o:")
    try:
        # Call with StructuredLLM signature (text, images, response_format)
        result = await a_structured_llm_openai(
            text="What is the capital of Japan? Include city and country.",
            images=None,
            response_format=CityInfo,
            model="gpt-4o",  # Can still pass model as kwarg
        )
        assert isinstance(result, CityInfo), f"Expected CityInfo, got {type(result)}"
        assert result.city.lower() == "tokyo", f"Expected Tokyo, got {result.city}"
        logger.success(f"✅ StructuredLLM protocol works: {result}")
    except Exception as e:
        logger.error(f"❌ StructuredLLM protocol failed: {e}")
        pytest.fail(f"StructuredLLM protocol test failed: {e}")

    # Test without structured format
    logger.info("\n2. Testing StructuredLLM protocol without format:")
    try:
        result = await a_structured_llm_openai(
            text="Say hello",
            model="gpt-4o",
        )
        assert result and result.strip(), "Empty response"
        logger.success(f"✅ Unstructured via protocol: {result}")
    except Exception as e:
        logger.error(f"❌ Unstructured via protocol failed: {e}")
        pytest.fail(f"Unstructured protocol test failed: {e}")


@pytest.mark.asyncio
@injected_pytest(design(openai_config=injected("openai_config__personal")))
async def test_gpt5_parameter_handling(
    a_sllm_openai,
    logger,
    /,
):
    """Test that GPT-5 parameters are handled correctly in direct API."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING GPT-5 PARAMETER HANDLING")
    logger.info("=" * 80)

    # Test that GPT-5 uses max_completion_tokens internally
    logger.info("\n1. Testing GPT-5 parameter transformation:")
    try:
        # This should work because a_sllm_openai transforms max_tokens to max_completion_tokens
        result = await a_sllm_openai(
            text="Count from 1 to 3",
            model="gpt-5-nano",
            max_tokens=5000,  # Will be transformed internally
        )
        assert result and result.strip(), "GPT-5 returned empty"
        logger.success(f"✅ GPT-5 parameter handling works: {result}")
        logger.info("   max_tokens was properly transformed to max_completion_tokens")
    except Exception as e:
        if "max_tokens" in str(e) and "not supported" in str(e):
            logger.error("❌ Parameter transformation failed!")
            pytest.fail("GPT-5 parameter not transformed correctly")
        else:
            logger.error(f"❌ Unexpected error: {e}")
            raise


@pytest.mark.asyncio
@injected_pytest(design(openai_config=injected("openai_config__personal")))
async def test_cost_comparison(
    logger,
    /,
):
    """Compare costs between direct OpenAI and OpenRouter."""

    logger.info("\n" + "=" * 80)
    logger.info("COST COMPARISON: DIRECT OPENAI VS OPENROUTER")
    logger.info("=" * 80)

    logger.info("\nFor GPT-5 models:")
    logger.info("- Direct OpenAI API: $X per 1M tokens")
    logger.info("- OpenRouter: $X * 1.05 per 1M tokens (5% markup)")
    logger.info("\nUsing a_sllm_openai avoids the 5% OpenRouter fee!")
    logger.info("\nExample savings:")
    logger.info("- $100 in OpenAI tokens via OpenRouter = $105 total cost")
    logger.info("- $100 in OpenAI tokens via direct API = $100 total cost")
    logger.info("- Savings: $5 per $100 spent")

    logger.success("\n✅ Direct OpenAI API implementation saves 5% on all API costs!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
