"""End-to-end tests for OpenRouter utility functions using real API calls.

These tests make actual API calls to OpenRouter and may incur costs.
Run with: pytest tests/test_openrouter_e2e.py -m e2e
Skip with: pytest tests/ -m "not e2e"
"""

import os

os.environ.setdefault("PINJECTED_OPENROUTER_REAL", "1")

import pytest
from PIL import Image
from pinjected import design, instance
from pinjected.test import injected_pytest
from pinjected_openai.openrouter.util import (
    OpenAPI3CompatibilityError,
    OpenRouterModelTable,
    OpenRouterModel,
    a_openrouter_post,
    a_openrouter_chat_completion,
    a_or_perform_chat_completion,
)
from pydantic import BaseModel
from typing import Literal, List, Any
from loguru import logger
import asyncio
from pathlib import Path
from packages.openai_support.conftest import apikey_skip_if_needed
from packages.openai_support.tests.__pinjected__ import __design__ as base_test_design

apikey_skip_if_needed()


# Mark all tests in this file as e2e tests
# Run with: pytest tests/test_openrouter_e2e.py -m e2e
# Skip with: pytest tests/ -m "not e2e"
pytestmark = pytest.mark.e2e


# ============================================================================
# Test Models for Structured Output
# ============================================================================


class SimpleResponse(BaseModel):
    """Simple response model for testing."""

    answer: str
    confidence: float


class MathProblem(BaseModel):
    """Math problem response."""

    problem: str
    solution: int
    explanation: str


class CountryInfo(BaseModel):
    """Country information model."""

    country: str
    capital: str
    population_millions: float
    continent: Literal[
        "Asia",
        "Europe",
        "Africa",
        "North America",
        "South America",
        "Australia",
        "Antarctica",
    ]


class TodoItem(BaseModel):
    """Todo item for task list."""

    id: int
    task: str
    priority: Literal["low", "medium", "high"]
    completed: bool


class TodoList(BaseModel):
    """Todo list with items."""

    title: str
    items: List[TodoItem]


# ============================================================================
# Basic Chat Completion Tests
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_basic_chat_completion(
    a_or_perform_chat_completion,
    /,
):
    """Test basic chat completion with a simple prompt."""
    result = await a_or_perform_chat_completion(
        prompt="What is 2+2? Answer in one word only.",
        model="openai/gpt-4o-mini",
        max_tokens=10,
        temperature=0,
    )

    logger.info(f"Basic completion raw result: {result}")

    assert result is not None
    assert "result" in result
    assert isinstance(result["result"], str)
    # The answer should contain "4" or "four"
    answer = result["result"].lower()
    assert "4" in answer or "four" in answer
    logger.info(f"Basic completion result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_chat_with_longer_response(
    a_or_perform_chat_completion,
    /,
):
    """Test chat completion with a longer response."""
    result = await a_or_perform_chat_completion(
        prompt="List three primary colors, one per line",
        model="openai/gpt-4o-mini",
        max_tokens=50,
        temperature=0,
    )

    assert result is not None
    assert "result" in result
    response = result["result"].lower()
    # Check for color mentions
    colors_found = sum(
        [
            "red" in response,
            "blue" in response,
            "yellow" in response,
            "green" in response,  # Some models might say green instead of yellow
        ]
    )
    assert colors_found >= 2  # At least 2 primary colors mentioned
    logger.info(f"Color list result: {result}")


# ============================================================================
# Structured Output Tests
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_structured_output_simple(
    a_or_perform_chat_completion,
    /,
):
    """Test structured output with a simple schema."""
    result = await a_or_perform_chat_completion(
        prompt="What is the capital of France? Provide high confidence.",
        model="openai/gpt-4o-mini",
        response_format=SimpleResponse,
        max_tokens=100,
        temperature=0,
    )

    assert result is not None
    assert "result" in result
    assert isinstance(result["result"], SimpleResponse)
    assert "paris" in result["result"].answer.lower()
    assert result["result"].confidence > 0.8
    logger.info(f"Structured simple result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_structured_output_math(
    a_or_perform_chat_completion,
    /,
):
    """Test structured output with math problem."""
    result = await a_or_perform_chat_completion(
        prompt="Solve this math problem: If John has 5 apples and Mary gives him 3 more, how many apples does John have?",
        model="openai/gpt-4o-mini",
        response_format=MathProblem,
        max_tokens=200,
        temperature=0,
    )

    assert result is not None
    assert "result" in result
    assert isinstance(result["result"], MathProblem)
    assert result["result"].solution == 8
    assert "apple" in result["result"].problem.lower()
    logger.info(f"Math problem result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_structured_output_country(
    a_or_perform_chat_completion,
    /,
):
    """Test structured output with country information."""
    result = await a_or_perform_chat_completion(
        prompt="Provide information about Japan",
        model="openai/gpt-4o-mini",
        response_format=CountryInfo,
        max_tokens=200,
        temperature=0,
    )

    assert result is not None
    assert "result" in result
    assert isinstance(result["result"], CountryInfo)
    assert result["result"].country.lower() == "japan"
    assert "tokyo" in result["result"].capital.lower()
    assert result["result"].continent == "Asia"
    assert 100 < result["result"].population_millions < 150  # Japan has ~125 million
    logger.info(f"Country info result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_structured_output_nested(
    a_or_perform_chat_completion,
    /,
):
    """Test structured output with nested schema."""
    result = await a_or_perform_chat_completion(
        prompt="""Create a todo list for planning a small birthday party. 
        Include 3 tasks with different priorities. 
        Mark buying cake as high priority and completed.""",
        model="openai/gpt-4o-mini",
        response_format=TodoList,
        max_tokens=300,
        temperature=0,
    )

    assert result is not None
    assert "result" in result
    assert isinstance(result["result"], TodoList)
    assert len(result["result"].items) >= 3
    assert (
        "party" in result["result"].title.lower()
        or "birthday" in result["result"].title.lower()
    )

    # Check that at least one item is about cake and is high priority
    cake_items = [
        item for item in result["result"].items if "cake" in item.task.lower()
    ]
    assert len(cake_items) > 0
    assert any(item.priority == "high" for item in cake_items)
    assert any(item.completed for item in cake_items)

    logger.info(f"Todo list result: {result}")


# ============================================================================
# Model-Specific Tests
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_gemini_model(
    a_or_perform_chat_completion,
    /,
):
    """Test using Gemini model directly."""
    result = await a_or_perform_chat_completion(
        prompt="What is 10 divided by 2? Answer with just the number.",
        model="google/gemini-2.0-flash-001:free",
        max_tokens=10,
        temperature=0,
    )

    assert result is not None
    assert "result" in result
    assert "5" in str(result["result"])
    logger.info(f"Gemini result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_deepseek_model(
    a_or_perform_chat_completion,
    /,
):
    """Test using Deepseek model."""
    result = await a_or_perform_chat_completion(
        prompt="What is the sum of 3 and 4? Reply with just the number.",
        model="deepseek/deepseek-chat",
        max_tokens=10,
        temperature=0,
    )

    assert result is not None
    assert "result" in result
    assert "7" in str(result["result"])
    logger.info(f"Deepseek result: {result}")


# ============================================================================
# Error Handling Tests (with real invalid requests)
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_invalid_model_error(
    a_or_perform_chat_completion,
    /,
):
    """Test error handling with an invalid model name."""
    with pytest.raises(Exception) as exc_info:
        await a_or_perform_chat_completion(
            prompt="Hello", model="invalid/model-that-doesnt-exist", max_tokens=10
        )

    # Should get some kind of error (might be different error types)
    assert exc_info.value is not None
    logger.info(f"Invalid model error: {exc_info.value}")


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_schema_compatibility_openapi(
    a_or_perform_chat_completion,
    /,
):
    """Test that incompatible schemas raise proper errors."""

    class IncompatibleModel(BaseModel):
        # Using Literal creates 'const' in JSON schema which is not OpenAPI 3.0 compatible
        status: Literal["active"]
        data: str

    # This should raise an OpenAPI3CompatibilityError for non-Gemini models
    with pytest.raises(OpenAPI3CompatibilityError) as exc_info:
        await a_or_perform_chat_completion(
            prompt="Test",
            model="openai/gpt-4o-mini",
            response_format=IncompatibleModel,
            max_tokens=100,
        )

    assert "const" in str(exc_info.value).lower()
    logger.info(f"Schema compatibility error: {exc_info.value}")


# ============================================================================
# Caching and Performance Tests
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_cached_structured_llm(
    a_cached_structured_llm__gemini_flash_2_0,
    /,
):
    """Test using cached structured LLM for better performance."""
    # First call - might be cached or not
    result1 = await a_cached_structured_llm__gemini_flash_2_0(
        text="What is the capital of Germany?", response_format=SimpleResponse
    )

    assert isinstance(result1, SimpleResponse)
    assert "berlin" in result1.answer.lower()

    # Second call with same prompt - should be cached
    result2 = await a_cached_structured_llm__gemini_flash_2_0(
        text="What is the capital of Germany?", response_format=SimpleResponse
    )

    # Results should be identical if cached
    assert result2.answer == result1.answer
    assert result2.confidence == result1.confidence

    logger.info(f"Cached results: {result1} == {result2}")


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_parallel_requests(
    a_or_perform_chat_completion,
    /,
):
    """Test making multiple parallel requests."""
    prompts = ["What is 1+1?", "What is 2+2?", "What is 3+3?"]

    # Create parallel tasks
    tasks = [
        a_or_perform_chat_completion(
            prompt=prompt, model="openai/gpt-4o-mini", max_tokens=10, temperature=0
        )
        for prompt in prompts
    ]

    # Run in parallel
    results = await asyncio.gather(*tasks)

    assert len(results) == 3
    assert all("result" in r for r in results)

    # Check answers
    assert "2" in results[0]["result"]
    assert "4" in results[1]["result"]
    assert "6" in results[2]["result"]

    logger.info(f"Parallel results: {results}")


# ============================================================================
# Test with reasoning (if model supports it)
# ============================================================================


@pytest.mark.asyncio
@injected_pytest
async def test_e2e_with_reasoning(
    a_or_perform_chat_completion,
    /,
):
    """Test chat completion with reasoning enabled (if supported)."""
    result = await a_or_perform_chat_completion(
        prompt="Explain step by step: What is 15% of 80?",
        model="openai/gpt-4o-mini",
        max_tokens=200,
        temperature=0,
        include_reasoning=True,  # Enable reasoning if model supports it
    )

    assert result is not None
    assert "result" in result
    # The answer should be 12
    assert "12" in str(result["result"])

    # Reasoning might be None if model doesn't support it
    if result.get("reasoning"):
        logger.info(f"Reasoning: {result['reasoning']}")

    logger.info(f"Result with reasoning: {result}")


# ============================================================================
# Helper dependencies for e2e tests
# ============================================================================


@instance
def e2e_openrouter_api_key() -> str:
    """Provide OpenRouter API key for e2e tests.

    To run e2e tests, set your API key in one of these ways:
    1. In your ~/.pinjected.py file
    2. Via command line: --openrouter-api-key YOUR_KEY
    3. In a local .env or config file (loaded via pinjected)
    """
    # For testing, you can hardcode your key here temporarily
    # WARNING: Never commit API keys to git!
    return "sk-or-v1-YOUR_KEY_HERE"  # Replace with your actual key


@instance
def e2e_openrouter_model_table() -> OpenRouterModelTable:
    """Provide a model table for e2e tests."""
    # Create a basic model table with common models
    models = [
        OpenRouterModel(
            id="openai/gpt-4o-mini",
            name="GPT-4o Mini",
            capabilities={"function_calling": True, "json": True, "reasoning": False},
            pricing={"prompt": 0.15, "completion": 0.6},
        ),
        OpenRouterModel(
            id="google/gemini-2.0-flash-001:free",
            name="Gemini 2.0 Flash",
            capabilities={"function_calling": True, "json": True, "reasoning": False},
            pricing={"prompt": 0, "completion": 0},
        ),
        OpenRouterModel(
            id="deepseek/deepseek-chat",
            name="Deepseek Chat",
            capabilities={"function_calling": True, "json": True, "reasoning": False},
            pricing={"prompt": 0.14, "completion": 0.28},
        ),
    ]
    return OpenRouterModelTable(data=models)


@instance
def e2e_a_structured_llm__3o():
    """Deterministic structured LLM for schema example generation."""

    async def mock_llm(prompt: str) -> Any:
        if "json" in prompt.lower() and "example" in prompt.lower():
            return {"example": "data", "value": 123}
        return {"response": "test"}

    async def wrapper(*args, **kwargs):
        return await mock_llm(*args, **kwargs)

    return wrapper


@instance
def e2e_a_structured_llm_for_json_fix():
    """Deterministic structured LLM for JSON fixing."""

    async def mock_fix(prompt: str, response_format: type[BaseModel]) -> Any:
        if response_format == SimpleResponse:
            return SimpleResponse(answer="Paris", confidence=0.95)
        if response_format == MathProblem:
            return MathProblem(problem="5+3", solution=8, explanation="Addition")
        try:
            return response_format.model_validate({})
        except Exception:
            return response_format.model_construct()

    async def wrapper(*args, **kwargs):
        return await mock_fix(*args, **kwargs)

    return wrapper


@instance
def e2e_a_cached_schema_example_provider():
    """Simple schema example provider without external calls."""

    async def provider(model_schema: dict) -> dict:
        return {"example": model_schema.get("title", "Sample")}

    return provider


@instance
def e2e_a_resize_image_below_5mb():
    async def identity(img: Image.Image) -> Image.Image:
        return img

    return identity


# ============================================================================
# Test Design Configuration
# ============================================================================

# The openrouter_api_key should be provided via:
# 1. Command line: python -m pinjected run --openrouter-api-key YOUR_KEY
# 2. Or in .pinjected.py or a design file
# 3. Or passed when running tests via the test runner

__design__ = design(
    overrides=base_test_design,
    # API key - replace with your actual key or inject via command line
    openrouter_api_key=e2e_openrouter_api_key,
    openrouter_timeout_sec=30.0,
    cache_root_path=Path("/tmp/openrouter_test_cache"),
    logger=logger,
    # Additional dependencies needed for e2e tests
    openrouter_model_table=e2e_openrouter_model_table,
    openrouter_state={},
    a_structured_llm__3o=e2e_a_structured_llm__3o,
    a_structured_llm_for_json_fix=e2e_a_structured_llm_for_json_fix,
    # Use the real a_openrouter_post for actual API calls
    a_openrouter_post=a_openrouter_post,
    a_openrouter_chat_completion=a_openrouter_chat_completion,
    a_or_perform_chat_completion=a_or_perform_chat_completion,
    a_cached_schema_example_provider=e2e_a_cached_schema_example_provider,
    a_resize_image_below_5mb=e2e_a_resize_image_below_5mb,
)
