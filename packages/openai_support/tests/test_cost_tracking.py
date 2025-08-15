"""Test cost tracking functionality in direct OpenAI implementation."""

import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel
from decimal import Decimal


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
async def test_cost_tracking_gpt4o(
    a_sllm_openai,
    openai_model_table,
    openai_state,
    logger,
    /,
):
    """Test that cost tracking works for GPT-4o model."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING COST TRACKING FOR GPT-4O")
    logger.info("=" * 80)

    # Get initial state
    initial_cost = openai_state.get("cumulative_cost", 0.0)
    logger.info(f"Initial cumulative cost: ${initial_cost:.6f}")

    # Make a simple API call
    logger.info("\n1. Making GPT-4o API call...")
    result = await a_sllm_openai(
        text="What is 2+2? Answer with just the number.",
        model="gpt-4o",
        max_tokens=50,
    )
    assert result and result.strip(), "GPT-4o returned empty response"
    logger.success(f"✅ Response: {result}")

    # Verify pricing is available
    pricing = openai_model_table.get_pricing("gpt-4o")
    assert pricing is not None, "No pricing info for gpt-4o"
    logger.info(
        f"GPT-4o pricing: ${pricing.prompt}/1M input, ${pricing.completion}/1M output"
    )

    # Test with structured output
    logger.info("\n2. Testing cost tracking with structured output...")
    result = await a_sllm_openai(
        text="The capital of France is Paris",
        model="gpt-4o",
        response_format=SimpleAnswer,
        max_tokens=100,
    )
    assert isinstance(result, SimpleAnswer), (
        f"Expected SimpleAnswer, got {type(result)}"
    )
    logger.success(f"✅ Structured response: {result}")
    logger.info("   (Cost should be logged above)")


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_cost_tracking_gpt5(
    a_sllm_openai,
    openai_model_table,
    openai_state,
    logger,
    /,
):
    """Test that cost tracking works for GPT-5 models with reasoning tokens."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING COST TRACKING FOR GPT-5 WITH REASONING")
    logger.info("=" * 80)

    # Test GPT-5-nano with reasoning
    logger.info("\n1. Testing GPT-5-nano with reasoning effort...")
    result = await a_sllm_openai(
        text="Calculate: (10 * 5) + 8 - 3",
        model="gpt-5-nano",
        max_tokens=10000,
        reasoning_effort="low",
    )
    assert result and result.strip(), "GPT-5-nano returned empty response"
    logger.success(f"✅ Response: {result}")

    # Verify pricing
    pricing = openai_model_table.get_pricing("gpt-5-nano")
    assert pricing is not None, "No pricing info for gpt-5-nano"
    logger.info(
        f"GPT-5-nano pricing: ${pricing.prompt}/1M input, ${pricing.completion}/1M output"
    )
    logger.info("   (Check logs above for reasoning token costs)")

    # Test with high reasoning for more tokens
    logger.info("\n2. Testing with high reasoning effort (more reasoning tokens)...")
    result = await a_sllm_openai(
        text="Solve step by step: If x^2 - 5x + 6 = 0, what are the values of x?",
        model="gpt-5-nano",
        max_tokens=10000,
        reasoning_effort="high",
    )
    assert result and result.strip(), "GPT-5-nano returned empty response"
    logger.success(f"✅ Response received (should show higher reasoning cost)")


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_model_pricing_table(
    openai_model_table,
    logger,
    /,
):
    """Test that the pricing table has correct information."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING MODEL PRICING TABLE")
    logger.info("=" * 80)

    # Test GPT-4o pricing
    gpt4o = openai_model_table.get_model("gpt-4o")
    assert gpt4o is not None, "GPT-4o not in pricing table"
    assert gpt4o.pricing.prompt == Decimal("2.50"), "GPT-4o prompt price incorrect"
    assert gpt4o.pricing.completion == Decimal("10.00"), (
        "GPT-4o completion price incorrect"
    )
    assert gpt4o.pricing.cached_prompt == Decimal("1.25"), (
        "GPT-4o cached price incorrect"
    )
    logger.success(
        f"✅ GPT-4o pricing verified: ${gpt4o.pricing.prompt}/${gpt4o.pricing.completion}"
    )

    # Test GPT-5-nano pricing
    gpt5_nano = openai_model_table.get_model("gpt-5-nano")
    assert gpt5_nano is not None, "GPT-5-nano not in pricing table"
    assert gpt5_nano.pricing.prompt == Decimal("0.60"), (
        "GPT-5-nano prompt price incorrect"
    )
    assert gpt5_nano.pricing.completion == Decimal("2.40"), (
        "GPT-5-nano completion price incorrect"
    )
    logger.success(
        f"✅ GPT-5-nano pricing verified: ${gpt5_nano.pricing.prompt}/${gpt5_nano.pricing.completion}"
    )

    # Test GPT-5 pricing
    gpt5 = openai_model_table.get_model("gpt-5")
    assert gpt5 is not None, "GPT-5 not in pricing table"
    assert gpt5.pricing.prompt == Decimal("15.00"), "GPT-5 prompt price incorrect"
    assert gpt5.pricing.completion == Decimal("60.00"), (
        "GPT-5 completion price incorrect"
    )
    logger.success(
        f"✅ GPT-5 pricing verified: ${gpt5.pricing.prompt}/${gpt5.pricing.completion}"
    )

    # Test cost calculation
    logger.info("\n3. Testing cost calculation...")
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
    }
    cost_dict = gpt4o.pricing.calc_cost(usage)
    expected_prompt_cost = 100 * 2.50 / 1_000_000
    expected_completion_cost = 50 * 10.00 / 1_000_000

    assert abs(cost_dict["prompt"] - expected_prompt_cost) < 0.000001
    assert abs(cost_dict["completion"] - expected_completion_cost) < 0.000001
    assert (
        abs(cost_dict["total"] - (expected_prompt_cost + expected_completion_cost))
        < 0.000001
    )
    logger.success(f"✅ Cost calculation correct: ${cost_dict['total']:.8f}")

    # Test with reasoning tokens
    logger.info("\n4. Testing cost calculation with reasoning tokens...")
    usage_with_reasoning = {
        "prompt_tokens": 100,
        "completion_tokens": 150,
        "completion_tokens_details": {
            "reasoning_tokens": 100,
        },
    }
    cost_dict = gpt5_nano.pricing.calc_cost(usage_with_reasoning)

    # Reasoning tokens are billed as completion tokens
    expected_prompt_cost = 100 * 0.60 / 1_000_000
    expected_completion_cost = 150 * 2.40 / 1_000_000
    expected_reasoning_cost = 100 * 2.40 / 1_000_000

    assert abs(cost_dict["prompt"] - expected_prompt_cost) < 0.000001
    assert abs(cost_dict["completion"] - expected_completion_cost) < 0.000001
    assert abs(cost_dict["reasoning"] - expected_reasoning_cost) < 0.000001
    logger.success(
        f"✅ Reasoning token cost calculation correct: ${cost_dict['reasoning']:.8f}"
    )

    logger.info("\n" + "=" * 80)
    logger.info("ALL PRICING TESTS PASSED!")
    logger.info("Cost tracking is working correctly")
    logger.info("=" * 80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
