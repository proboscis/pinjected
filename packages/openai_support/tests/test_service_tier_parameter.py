"""Test service_tier parameter support in a_sllm_openai function."""

from packages.openai_support.conftest import apikey_skip_if_needed
import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel

apikey_skip_if_needed()


class SimpleResponse(BaseModel):
    message: str
    confidence: float


@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_service_tier_parameter_flex(
    a_sllm_openai,
    logger,
    /,
):
    """Test that service_tier='flex' parameter is properly passed to OpenAI API."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTING SERVICE_TIER PARAMETER - FLEX")
    logger.info("=" * 80)

    try:
        result = await a_sllm_openai(
            text="Say 'Hello from OpenAI with flex tier' in exactly 7 words",
            model="gpt-4o",
            service_tier="flex",
            max_tokens=50,
        )
        assert result and result.strip(), "OpenAI returned empty response"
        logger.success(f"✅ service_tier='flex' response: {result}")
        logger.info("   service_tier parameter successfully passed to OpenAI API")
    except Exception as e:
        logger.error(f"❌ service_tier='flex' test failed: {e}")
        pytest.fail(f"service_tier='flex' test failed: {e}")


@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_service_tier_parameter_all_valid_values(
    a_sllm_openai,
    logger,
    /,
):
    """Test all valid service_tier values are accepted."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTING SERVICE_TIER PARAMETER - ALL VALID VALUES")
    logger.info("=" * 80)

    valid_tiers = ["auto", "default", "flex", "priority"]

    for tier in valid_tiers:
        logger.info(f"\nTesting service_tier='{tier}':")
        try:
            result = await a_sllm_openai(
                text=f"Say 'Testing {tier} tier' in exactly 3 words",
                model="gpt-4o",
                service_tier=tier,
                max_tokens=20,
            )
            assert result and result.strip(), f"Empty response for tier '{tier}'"
            logger.success(f"✅ service_tier='{tier}' works: {result}")
        except Exception as e:
            logger.error(f"❌ service_tier='{tier}' failed: {e}")
            pytest.fail(f"service_tier='{tier}' test failed: {e}")


@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_service_tier_parameter_none_default(
    a_sllm_openai,
    logger,
    /,
):
    """Test that service_tier=None (default) works correctly."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTING SERVICE_TIER PARAMETER - DEFAULT (NONE)")
    logger.info("=" * 80)

    try:
        result = await a_sllm_openai(
            text="Say 'Default tier test' in exactly 3 words",
            model="gpt-4o",
            max_tokens=20,
        )
        assert result and result.strip(), "Empty response with default service_tier"
        logger.success(f"✅ Default service_tier works: {result}")
    except Exception as e:
        logger.error(f"❌ Default service_tier test failed: {e}")
        pytest.fail(f"Default service_tier test failed: {e}")


@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_service_tier_with_structured_output(
    a_sllm_openai,
    logger,
    /,
):
    """Test service_tier parameter works with structured output."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTING SERVICE_TIER WITH STRUCTURED OUTPUT")
    logger.info("=" * 80)

    try:
        result = await a_sllm_openai(
            text="Provide a simple greeting message with high confidence",
            model="gpt-4o",
            service_tier="flex",
            response_format=SimpleResponse,
            max_tokens=100,
        )
        assert isinstance(result, SimpleResponse), (
            f"Expected SimpleResponse, got {type(result)}"
        )
        assert result.message and result.message.strip(), (
            "Empty message in structured response"
        )
        assert 0 <= result.confidence <= 1, f"Invalid confidence: {result.confidence}"
        logger.success(f"✅ service_tier with structured output: {result}")
    except Exception as e:
        logger.error(f"❌ service_tier with structured output failed: {e}")
        pytest.fail(f"service_tier with structured output failed: {e}")


@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_service_tier_parameter_validation(
    a_sllm_openai,
    logger,
    /,
):
    """Test that invalid service_tier values are handled gracefully."""
    logger.info("\n" + "=" * 80)
    logger.info("TESTING SERVICE_TIER PARAMETER VALIDATION")
    logger.info("=" * 80)

    try:
        result = await a_sllm_openai(
            text="Say 'Invalid tier test' in exactly 3 words",
            model="gpt-4o",
            service_tier="invalid_tier",
            max_tokens=20,
        )
        assert result and result.strip(), (
            "Function should still work with invalid service_tier"
        )
        logger.success(f"✅ Invalid service_tier handled gracefully: {result}")
        logger.info("   Function continued execution despite invalid service_tier")
    except Exception as e:
        logger.error(f"❌ Invalid service_tier handling failed: {e}")
        pytest.fail(f"Invalid service_tier handling failed: {e}")
