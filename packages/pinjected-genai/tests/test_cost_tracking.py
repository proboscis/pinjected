"""Test cost tracking for Google Gen AI models."""

import pytest
from dataclasses import dataclass
from unittest.mock import Mock
from pinjected_genai.genai_pricing import (
    GenAIModelTable,
    ModelPricing,
    log_generation_cost,
    genai_state,
    GenAIState,
)
from pinjected import design
from pinjected.test import injected_pytest
from loguru import logger


@dataclass
class SimpleResponse:
    """Simple response for testing structured output."""

    answer: str
    confidence: float


# Test design for dependency injection
def get_test_di():
    """Get test design for dependency injection."""
    return design(
        logger=logger,
        genai_model_table=GenAIModelTable(),
        genai_state=genai_state,
    )


@injected_pytest(get_test_di())
def test_model_pricing_calculation_with_image_tokens(logger, /):
    """Test ModelPricing cost calculation with image token pricing."""
    # Test with image-preview model that charges for input/output images
    pricing = ModelPricing(
        text_input=0.30,  # Per million tokens
        text_output=2.50,  # Per million tokens
        image_input=0.30,  # $0.30/1M tokens for input images
        image_output=30.0,  # $30/1M tokens for image generation
    )

    # Test with actual token counts
    usage = {
        "text_input_tokens": 100,  # 100 tokens directly
        "text_output_tokens": 0,
        "image_input_tokens": 1290,  # Example: 1 input image uses 1290 tokens
        "image_output_tokens": 1290,  # Example: 1 output image uses 1290 tokens
    }

    cost = pricing.calc_cost(usage)

    # Text input: 100 tokens = 0.0001M tokens * 0.30 = 0.000030
    # Image input: 1290 tokens = 0.00129M tokens * 0.30 = 0.000387
    # Image output: 1290 tokens = 0.00129M tokens * 30.0 = 0.0387
    assert cost["text_input"] == pytest.approx(0.000030, rel=1e-6)
    assert cost["text_output"] == 0.0
    assert cost["image_input"] == pytest.approx(0.000387, rel=1e-6)
    assert cost["image_output"] == pytest.approx(0.0387, rel=1e-6)
    assert cost["total"] == pytest.approx(0.039117, rel=1e-6)


@injected_pytest(get_test_di())
def test_model_pricing_calculation(logger, /):
    """Test ModelPricing cost calculation with text-only."""
    pricing = ModelPricing(
        text_input=0.30,  # Per million tokens
        text_output=2.50,  # Per million tokens
        image_input=0.00,  # Free
        image_output=0.00,  # Not supported
    )

    # Test text-only usage
    usage = {
        "text_input_tokens": 1000,  # 1K tokens
        "text_output_tokens": 2000,  # 2K tokens
        "image_input_tokens": 0,
        "image_output_tokens": 0,
    }

    cost = pricing.calc_cost(usage)

    # 1K tokens = 0.001M tokens
    # Input: 0.001 * 0.30 = 0.0003
    # Output: 0.002 * 2.50 = 0.005
    assert cost["text_input"] == pytest.approx(0.0003, rel=1e-6)
    assert cost["text_output"] == pytest.approx(0.005, rel=1e-6)
    assert cost["image_input"] == 0.0
    assert cost["image_output"] == 0.0
    assert cost["total"] == pytest.approx(0.0053, rel=1e-6)


@injected_pytest(get_test_di())
def test_genai_model_table(genai_model_table, logger, /):
    """Test GenAIModelTable retrieves correct pricing."""
    table = genai_model_table

    # Test known models
    flash_pricing = table.get_pricing("gemini-2.5-flash")
    assert flash_pricing is not None
    assert flash_pricing.text_input == 0.30  # $0.30/1M tokens
    assert flash_pricing.text_output == 2.50  # $2.50/1M tokens
    assert flash_pricing.image_output == 0.00  # Text-only model

    flash_image_pricing = table.get_pricing("gemini-2.5-flash-image-preview")
    assert flash_image_pricing is not None
    assert flash_image_pricing.text_input == 0.30  # Same as regular flash
    assert flash_image_pricing.text_output == 2.50  # Same as regular flash
    assert flash_image_pricing.image_input == 0.30  # $0.30/1M tokens
    assert (
        flash_image_pricing.image_output == 30.0
    )  # $30 per million tokens for image generation

    pro_pricing = table.get_pricing("gemini-2.5-pro")
    assert pro_pricing is not None
    assert pro_pricing.text_input == 12.50  # $12.50/1M tokens
    assert pro_pricing.text_output == 150.0  # $150/1M tokens
    assert pro_pricing.image_output == 0.00  # Text-only model

    # Test unknown model
    unknown = table.get_pricing("unknown-model-xyz")
    assert unknown is None


@injected_pytest(get_test_di())
def test_cumulative_cost_tracking(genai_state, logger, /):
    """Test cumulative cost tracking with GenAIState dataclass."""
    # Start with initial state
    assert isinstance(genai_state, GenAIState)

    assert genai_state.cumulative_cost == 0.0
    assert genai_state.cost_breakdown.text_input == 0.0
    assert genai_state.cost_breakdown.text_output == 0.0
    assert genai_state.cost_breakdown.image_input == 0.0
    assert genai_state.cost_breakdown.image_output == 0.0
    assert genai_state.request_count == 0

    # Simulate first cost update
    cost1 = {
        "text_input": 0.001,
        "text_output": 0.002,
        "image_input": 0.0,
        "image_output": 0.04,
        "total": 0.043,
    }

    # Manually update state as log_generation_cost would do
    genai_state.cumulative_cost += cost1["total"]
    genai_state.total_cost_usd = genai_state.cumulative_cost
    # Create new CostBreakdown instance (immutable)
    from pinjected_genai.genai_pricing import CostBreakdown

    new_cost_breakdown = CostBreakdown(
        text_input=cost1["text_input"],
        text_output=cost1["text_output"],
        image_input=cost1["image_input"],
        image_output=cost1["image_output"],
    )
    genai_state.cost_breakdown = genai_state.cost_breakdown.add(new_cost_breakdown)
    genai_state.request_count += 1

    assert genai_state.cumulative_cost == 0.043
    assert genai_state.cost_breakdown.text_input == 0.001
    assert genai_state.cost_breakdown.text_output == 0.002
    assert genai_state.cost_breakdown.image_output == 0.04
    assert genai_state.request_count == 1

    # Simulate second cost update
    cost2 = {
        "text_input": 0.002,
        "text_output": 0.003,
        "image_input": 0.0,
        "image_output": 0.04,
        "total": 0.045,
    }

    genai_state.cumulative_cost += cost2["total"]
    genai_state.total_cost_usd = genai_state.cumulative_cost
    # Create another new CostBreakdown instance and add it
    new_cost_breakdown2 = CostBreakdown(
        text_input=cost2["text_input"],
        text_output=cost2["text_output"],
        image_input=cost2["image_input"],
        image_output=cost2["image_output"],
    )
    genai_state.cost_breakdown = genai_state.cost_breakdown.add(new_cost_breakdown2)
    genai_state.request_count += 1

    assert genai_state.cumulative_cost == pytest.approx(0.088, rel=1e-6)
    assert genai_state.cost_breakdown.text_input == pytest.approx(0.003, rel=1e-6)
    assert genai_state.cost_breakdown.text_output == pytest.approx(0.005, rel=1e-6)
    assert genai_state.cost_breakdown.image_output == pytest.approx(0.08, rel=1e-6)
    assert genai_state.request_count == 2


@injected_pytest(get_test_di())
def test_log_generation_cost(genai_model_table, genai_state, logger, /):
    """Test logging generation costs."""
    logger = Mock()
    logger.error = Mock()
    logger.info = Mock()
    table = genai_model_table
    state = genai_state

    usage = {
        "text_input_tokens": 250,  # ~1000 chars / 4
        "text_output_tokens": 500,  # ~2000 chars / 4
        "image_input_tokens": 0,
        "image_output_tokens": 1290,  # Standard image generation tokens
    }

    returned_state = log_generation_cost(
        usage=usage,
        model="gemini-2.5-flash-image-preview",
        genai_model_table=table,
        genai_state=state,
        logger=logger,
    )

    # Check state was mutated (same object returned)
    assert returned_state is state
    assert state.cumulative_cost > 0
    assert state.request_count == 1

    # Check logger was called
    logger.info.assert_called()
    log_message = logger.info.call_args[0][0]
    assert "GenAI Cost:" in log_message
    assert "Total:" in log_message
    assert "Cumulative:" in log_message

    # Test with unknown model - now raises ValueError
    logger.reset_mock()

    with pytest.raises(ValueError) as exc_info:
        log_generation_cost(
            usage=usage,
            model="unknown-model",
            genai_model_table=table,
            genai_state=state,
            logger=logger,
        )

    assert "No pricing information available" in str(exc_info.value)
    assert "unknown-model" in str(exc_info.value)

    # Error should be logged before raising
    logger.error.assert_called_once()
    error_message = logger.error.call_args[0][0]
    assert "No pricing information" in error_message
    assert "unknown-model" in error_message


@injected_pytest(get_test_di())
def test_log_generation_cost_periodic_breakdown(
    genai_model_table, genai_state, logger, /
):
    """Test that detailed breakdown is logged every 10 requests."""
    logger = Mock()
    logger.info = Mock()
    table = genai_model_table
    state = genai_state

    usage = {
        "text_input_tokens": 25,  # ~100 chars / 4
        "text_output_tokens": 50,  # ~200 chars / 4
        "image_input_tokens": 0,
        "image_output_tokens": 1290,
    }

    # Make 10 requests
    for i in range(10):
        returned_state = log_generation_cost(
            usage=usage,
            model="gemini-2.5-flash-image-preview",
            genai_model_table=table,
            genai_state=state,
            logger=logger,
        )
        assert returned_state is state  # Should return same mutated object

    # Check that breakdown was logged on the 10th request
    calls = logger.info.call_args_list
    # Should have 2 info calls for the 10th request
    # (one for regular cost, one for breakdown)
    last_two_calls = calls[-2:]

    # Find the breakdown log
    breakdown_logged = False
    for call in last_two_calls:
        if "Cost breakdown" in call[0][0]:
            breakdown_logged = True
            break

    assert breakdown_logged, "Detailed breakdown should be logged on 10th request"


def create_mock_image_response(text_parts=None, image_count=1):
    """Create a mock response for image generation."""
    response = Mock()
    response.candidates = []

    if text_parts or image_count > 0:
        candidate = Mock()
        candidate.content = Mock()
        candidate.content.parts = []

        # Add text parts
        if text_parts:
            for text in text_parts:
                part = Mock()
                part.text = text
                part.inline_data = None
                candidate.content.parts.append(part)

        # Add image parts
        for i in range(image_count):
            part = Mock()
            part.text = None
            part.inline_data = Mock()
            part.inline_data.data = f"fake_image_data_{i}".encode()
            part.inline_data.mime_type = "image/png"
            candidate.content.parts.append(part)

        response.candidates.append(candidate)

    return response


@pytest.mark.skip(
    reason="Requires actual Gen AI client with mocking - integration test"
)
@injected_pytest(get_test_di())
async def test_cost_tracking_in_generate_image(
    genai_model_table, genai_state, logger, /
):
    """Test that cost is tracked when generating an image."""
    # This test would require proper mocking of Gen AI client
    # which is complex due to dependency injection
    pass


@pytest.mark.skip(
    reason="Requires actual Gen AI client with mocking - integration test"
)
@injected_pytest(get_test_di())
async def test_cost_tracking_in_edit_image(genai_model_table, genai_state, logger, /):
    """Test that cost is tracked when editing an image."""
    # This test would require proper mocking of Gen AI client
    # which is complex due to dependency injection
    pass


@pytest.mark.skip(
    reason="Requires actual Gen AI client with mocking - integration test"
)
@injected_pytest(get_test_di())
async def test_cost_tracking_in_describe_image(
    genai_model_table, genai_state, logger, /
):
    """Test that cost is tracked when describing an image."""
    # This test would require proper mocking of Gen AI client
    # which is complex due to dependency injection
    pass
