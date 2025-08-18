"""Test GPT-5 thinking mode functionality in direct OpenAI implementation."""

import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel


class ReasoningResponse(BaseModel):
    """Response model for testing reasoning tasks."""

    answer: int
    reasoning: str


class SimpleAnswer(BaseModel):
    """Simple answer model for testing."""

    answer: str


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_gpt5_thinking_mode_parameters(
    a_sllm_openai,
    logger,
    /,
):
    """Test that GPT-5 thinking mode parameters are properly handled."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING GPT-5 THINKING MODE PARAMETER SUPPORT")
    logger.info("=" * 80)

    # Test 1: Test with minimal reasoning effort
    logger.info("\n1. Testing MINIMAL reasoning effort:")
    result = await a_sllm_openai(
        text="What is 2+2? Answer with just the number.",
        model="gpt-5-nano",
        max_tokens=10000,
        reasoning_effort="minimal",
    )
    assert result and result.strip(), "GPT-5 returned empty response"
    logger.success(f"✅ Minimal reasoning: {result}")
    logger.info("   (Fastest response for simple tasks)")

    # Test 2: Test with low reasoning effort
    logger.info("\n2. Testing LOW reasoning effort:")
    result = await a_sllm_openai(
        text="Calculate: (10 * 5) + (8 / 2) - 3",
        model="gpt-5-nano",
        max_tokens=10000,
        reasoning_effort="low",
    )
    assert result and result.strip(), "GPT-5 returned empty response"
    assert "51" in result, f"Expected '51' in response, got: {result}"
    logger.success(f"✅ Low reasoning: {result}")

    # Test 3: Test with high reasoning effort
    logger.info("\n3. Testing HIGH reasoning effort:")
    result = await a_sllm_openai(
        text="Solve: If x^2 - 5x + 6 = 0, what are the values of x?",
        model="gpt-5-nano",
        max_tokens=10000,
        reasoning_effort="high",
    )
    assert result and result.strip(), "GPT-5 returned empty response"
    logger.success(f"✅ High reasoning: {result[:150]}...")
    logger.info("   (Deep reasoning for complex problems)")


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_gpt5_verbosity_control(
    a_sllm_openai,
    logger,
    /,
):
    """Test GPT-5 verbosity control with thinking mode."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING GPT-5 VERBOSITY CONTROL")
    logger.info("=" * 80)

    # Test low verbosity
    logger.info("\n1. Testing LOW verbosity:")
    result = await a_sllm_openai(
        text="What is the capital of France?",
        model="gpt-5-nano",
        max_tokens=10000,
        verbosity="low",
    )
    assert result and result.strip(), "GPT-5 returned empty response"
    logger.success(f"✅ Low verbosity: {result}")

    # Test high verbosity
    logger.info("\n2. Testing HIGH verbosity:")
    result = await a_sllm_openai(
        text="What is the capital of France?",
        model="gpt-5-nano",
        max_tokens=10000,
        verbosity="high",
    )
    assert result and result.strip(), "GPT-5 returned empty response"
    logger.success(f"✅ High verbosity: {result[:100]}...")


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_gpt5_thinking_with_structured_output(
    a_sllm_openai,
    logger,
    /,
):
    """Test GPT-5 thinking mode with structured output."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING GPT-5 THINKING MODE WITH STRUCTURED OUTPUT")
    logger.info("=" * 80)

    # Test structured output with reasoning
    logger.info("\n1. Testing structured output with reasoning:")
    result = await a_sllm_openai(
        text="What is 5 times 5?",
        model="gpt-5-nano",
        response_format=SimpleAnswer,
        max_tokens=10000,
        reasoning_effort="low",
        verbosity="medium",
    )
    assert isinstance(result, SimpleAnswer), (
        f"Expected SimpleAnswer, got {type(result)}"
    )
    assert "25" in result.answer, f"Expected '25' in answer, got: {result.answer}"
    logger.success(f"✅ Structured output with thinking mode: {result}")


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_non_gpt5_thinking_mode_warnings(
    a_sllm_openai,
    logger,
    /,
):
    """Test that non-GPT-5 models properly warn about thinking mode parameters."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING NON-GPT-5 THINKING MODE WARNINGS")
    logger.info("=" * 80)

    # GPT-4o should warn about thinking mode parameters
    logger.info("\n1. Testing GPT-4o with thinking mode params (should warn):")
    result = await a_sllm_openai(
        text="What is 2+2?",
        model="gpt-4o",
        max_tokens=100,
        reasoning_effort="high",
        verbosity="low",
    )
    assert result and result.strip(), "GPT-4o returned empty response"
    logger.success(f"✅ GPT-4o works (thinking params ignored): {result}")
    logger.info("   (Check logs for warnings about unsupported parameters)")


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_invalid_thinking_parameters(
    a_sllm_openai,
    logger,
    /,
):
    """Test handling of invalid thinking mode parameters."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING INVALID THINKING MODE PARAMETERS")
    logger.info("=" * 80)

    # Test invalid reasoning_effort
    logger.info("\n1. Testing invalid reasoning_effort (should warn but continue):")
    result = await a_sllm_openai(
        text="What is 2+2?",
        model="gpt-5-nano",
        max_tokens=10000,
        reasoning_effort="super-ultra-high",
    )
    assert result and result.strip(), "GPT-5 returned empty response"
    logger.success(f"✅ Handled invalid reasoning_effort gracefully: {result}")
    logger.info("   (Check logs for warning about invalid value)")

    # Test invalid verbosity
    logger.info("\n2. Testing invalid verbosity (should warn but continue):")
    result = await a_sllm_openai(
        text="What is 2+2?",
        model="gpt-5-nano",
        max_tokens=10000,
        verbosity="extremely-verbose",
    )
    assert result and result.strip(), "GPT-5 returned empty response"
    logger.success(f"✅ Handled invalid verbosity gracefully: {result}")
    logger.info("   (Check logs for warning about invalid value)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
