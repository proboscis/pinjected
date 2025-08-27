"""Comprehensive tests for a_openrouter_chat_completion with response_format BaseModel."""

import pytest
from typing import Optional, List
from pinjected.test import injected_pytest
from pinjected_openai.openrouter.util import (
    parse_json_response,
)
from pydantic import BaseModel, Field
from loguru import logger


class SimpleModel(BaseModel):
    """Simple model for basic testing."""

    name: str
    age: int


class ModelWithOptional(BaseModel):
    """Model with optional fields."""

    required_field: str
    optional_field: Optional[str] = None
    optional_number: Optional[int] = None


class NestedModel(BaseModel):
    """Model with nested structure."""

    title: str
    metadata: dict

    class Config:
        extra = "forbid"


class Address(BaseModel):
    """Address model for nested structures."""

    street: str
    city: str
    country: str
    zip_code: Optional[str] = None


class Person(BaseModel):
    """Person model for nested structures."""

    name: str
    age: int
    email: str
    address: Address


class ComplexNestedModel(BaseModel):
    """Complex nested model with multiple levels."""

    people: List[Person]
    organization: str
    total_count: int


class ModelWithLists(BaseModel):
    """Model containing lists and complex types."""

    tags: List[str]
    scores: List[float]
    items: List[dict]
    primary_item: dict


class ModelWithValidation(BaseModel):
    """Model with field validators."""

    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    score: float = Field(..., ge=0.0, le=1.0)
    count: int = Field(..., gt=0)


class ModelWithDescription(BaseModel):
    """Model with field descriptions for better prompting."""

    summary: str = Field(..., description="A brief summary of the content")
    sentiment: str = Field(..., description="Sentiment: positive, negative, or neutral")
    confidence: float = Field(
        ..., description="Confidence score between 0 and 1", ge=0, le=1
    )
    keywords: List[str] = Field(..., description="List of relevant keywords")


class Entity(BaseModel):
    """Entity extracted from text."""

    text: str
    type: str  # person, organization, location
    confidence: float


class Sentiment(BaseModel):
    """Sentiment analysis result."""

    label: str  # positive, negative, neutral
    score: float


class AnalysisResult(BaseModel):
    """Real-world example: text analysis result."""

    summary: str
    entities: List[Entity]
    sentiment: Sentiment
    key_points: List[str]
    word_count: int


# Test basic functionality
@pytest.mark.asyncio
@injected_pytest
async def test_simple_model_response(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test basic response_format with simple model."""
    result = await a_openrouter_chat_completion(
        prompt="Create a person named John who is 30 years old.",
        model="openai/gpt-4o-mini",
        max_tokens=100,
        temperature=0,
        response_format=SimpleModel,
    )

    assert isinstance(result, SimpleModel)
    assert result.name == "John"
    assert result.age == 30
    logger.info(f"Simple model result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_model_with_optional_fields(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test model with optional fields."""
    result = await a_openrouter_chat_completion(
        prompt="Create data with required_field='test' and leave optional fields empty.",
        model="openai/gpt-4o-mini",
        max_tokens=100,
        temperature=0,
        response_format=ModelWithOptional,
    )

    assert isinstance(result, ModelWithOptional)
    assert result.required_field == "test"
    assert result.optional_field is None or isinstance(result.optional_field, str)
    logger.info(f"Optional fields result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_nested_model(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test nested model structure."""
    result = await a_openrouter_chat_completion(
        prompt="Create a response with title='Test Report' and metadata containing status='completed' and version=1.",
        model="openai/gpt-4o-mini",
        max_tokens=200,
        temperature=0,
        response_format=NestedModel,
    )

    assert isinstance(result, NestedModel)
    assert result.title == "Test Report"
    assert isinstance(result.metadata, dict)
    assert result.metadata.get("status") == "completed"
    assert result.metadata.get("version") == 1
    logger.info(f"Nested model result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_complex_nested_model(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test complex nested model with multiple levels."""
    prompt = """Create data for a tech company with 2 people:
    1. Alice, 28, alice@example.com, lives at 123 Main St, New York, USA
    2. Bob, 35, bob@example.com, lives at 456 Oak Ave, San Francisco, USA
    Organization: TechCorp"""

    result = await a_openrouter_chat_completion(
        prompt=prompt,
        model="openai/gpt-4o-mini",
        max_tokens=500,
        temperature=0,
        response_format=ComplexNestedModel,
    )

    assert isinstance(result, ComplexNestedModel)
    assert result.organization == "TechCorp"
    assert result.total_count == 2
    assert len(result.people) == 2

    # Check first person
    alice = result.people[0]
    assert alice.name == "Alice"
    assert alice.age == 28
    assert alice.email == "alice@example.com"
    assert alice.address.city == "New York"

    logger.info(f"Complex nested result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_model_with_lists(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test model containing lists."""
    result = await a_openrouter_chat_completion(
        prompt="Create data with tags=['python', 'testing'], scores=[0.9, 0.8], items=[{'id': 1}, {'id': 2}], and primary_item={'name': 'main'}",
        model="openai/gpt-4o-mini",
        max_tokens=200,
        temperature=0,
        response_format=ModelWithLists,
    )

    assert isinstance(result, ModelWithLists)
    assert "python" in result.tags
    assert "testing" in result.tags
    assert len(result.scores) == 2
    assert all(isinstance(s, float) for s in result.scores)
    assert len(result.items) == 2
    assert result.primary_item["name"] == "main"
    logger.info(f"Lists model result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_model_with_validation(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test model with field validators."""
    result = await a_openrouter_chat_completion(
        prompt="Create data with email='test@example.com', score=0.75, and count=5",
        model="openai/gpt-4o-mini",
        max_tokens=100,
        temperature=0,
        response_format=ModelWithValidation,
    )

    assert isinstance(result, ModelWithValidation)
    assert "@" in result.email
    assert 0 <= result.score <= 1
    assert result.count > 0
    logger.info(f"Validation model result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_model_with_descriptions(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test that field descriptions help guide the model."""
    result = await a_openrouter_chat_completion(
        prompt="Analyze this text: 'The new product launch was incredibly successful, exceeding all expectations.'",
        model="openai/gpt-4o-mini",
        max_tokens=200,
        temperature=0,
        response_format=ModelWithDescription,
    )

    assert isinstance(result, ModelWithDescription)
    assert len(result.summary) > 0
    assert result.sentiment in ["positive", "negative", "neutral"]
    assert result.sentiment == "positive"  # Should detect positive sentiment
    assert 0 <= result.confidence <= 1
    assert len(result.keywords) > 0
    logger.info(f"Description model result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_real_world_analysis(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test real-world text analysis scenario."""
    text = """
    Apple Inc. announced today that Tim Cook will be visiting Tokyo next month 
    to meet with Japanese partners. The company reported strong Q4 earnings, 
    beating analyst expectations. Market sentiment remains positive.
    """

    result = await a_openrouter_chat_completion(
        prompt=f"Analyze this text and extract entities, sentiment, and key points: {text}",
        model="openai/gpt-4o-mini",
        max_tokens=500,
        temperature=0,
        response_format=AnalysisResult,
    )

    assert isinstance(result, AnalysisResult)
    assert len(result.summary) > 0
    assert len(result.entities) > 0

    # Should detect Apple and Tim Cook as entities
    entity_names = [e.text for e in result.entities]
    assert any("Apple" in name or "Tim Cook" in name for name in entity_names)

    assert result.sentiment.label in ["positive", "negative", "neutral"]
    assert result.word_count > 0
    assert len(result.key_points) > 0

    logger.info(f"Analysis result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_model_without_json_support(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test with a model that may not have native JSON support."""
    # Using a model that might not support JSON to test the fallback mechanism
    result = await a_openrouter_chat_completion(
        prompt="Create a person named Jane who is 25 years old.",
        model="meta-llama/llama-3-8b-instruct",  # Model without native JSON support
        max_tokens=100,
        temperature=0,
        response_format=SimpleModel,
    )

    assert isinstance(result, SimpleModel)
    assert result.name == "Jane"
    assert result.age == 25
    logger.info(f"Non-JSON model result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_multiple_models_consistency(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test consistency across different models."""
    prompt = "Create data with name='TestUser' and age=42"
    models = [
        "openai/gpt-4o-mini",
        "anthropic/claude-3-haiku",
    ]

    results = []
    for model in models:
        try:
            result = await a_openrouter_chat_completion(
                prompt=prompt,
                model=model,
                max_tokens=100,
                temperature=0,
                response_format=SimpleModel,
            )
            results.append((model, result))
            logger.info(f"Model {model} result: {result}")
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")

    # All successful results should have the same values
    for model, result in results:
        assert isinstance(result, SimpleModel)
        assert result.name == "TestUser"
        assert result.age == 42


@pytest.mark.asyncio
@injected_pytest
async def test_error_recovery_malformed_json(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test that the system can recover from malformed JSON responses."""
    # Use a prompt that might produce slightly malformed JSON
    result = await a_openrouter_chat_completion(
        prompt="Generate a response but be creative: name should be 'Test' and age should be thirty (30)",
        model="openai/gpt-4o-mini",
        max_tokens=200,
        temperature=0.8,  # Higher temperature for more variation
        response_format=SimpleModel,
    )

    # Should still parse correctly through the fix mechanism
    assert isinstance(result, SimpleModel)
    assert result.name == "Test"
    assert result.age == 30
    logger.info(f"Error recovery result: {result}")


@pytest.mark.asyncio
@injected_pytest
async def test_parse_json_response_helper(
    a_structured_llm_for_json_fix,
    logger,
    /,
):
    """Test the parse_json_response helper function directly."""

    # Test valid JSON
    valid_json = '{"name": "Alice", "age": 30}'
    result = await parse_json_response(
        data=valid_json,
        response_format=SimpleModel,
        logger=logger,
        a_structured_llm_for_json_fix=a_structured_llm_for_json_fix,
        prompt="Test prompt",
    )
    assert isinstance(result, SimpleModel)
    assert result.name == "Alice"
    assert result.age == 30

    # Test JSON with extra text (needs cleaning)
    json_with_text = 'Here is the JSON: {"name": "Bob", "age": 25} That\'s all!'
    result = await parse_json_response(
        data=json_with_text,
        response_format=SimpleModel,
        logger=logger,
        a_structured_llm_for_json_fix=a_structured_llm_for_json_fix,
        prompt="Test prompt",
    )
    assert isinstance(result, SimpleModel)
    assert result.name == "Bob"
    assert result.age == 25

    # Test malformed JSON that needs LLM fix
    malformed = "name: Charlie, age: thirty-five"
    result = await parse_json_response(
        data=malformed,
        response_format=SimpleModel,
        logger=logger,
        a_structured_llm_for_json_fix=a_structured_llm_for_json_fix,
        prompt="Create person Charlie aged 35",
    )
    assert isinstance(result, SimpleModel)
    # The LLM should fix this


@pytest.mark.asyncio
@injected_pytest
async def test_with_images(
    a_openrouter_chat_completion,
    openrouter_api,
    /,
):
    """Test response_format with image input."""
    from PIL import Image

    # Create a simple test image
    img = Image.new("RGB", (100, 100), color="red")

    result = await a_openrouter_chat_completion(
        prompt="Describe what you see and provide name='RedSquare' and age=1",
        model="openai/gpt-4o-mini",  # Model that supports vision
        max_tokens=100,
        temperature=0,
        images=[img],
        response_format=SimpleModel,
    )

    assert isinstance(result, SimpleModel)
    assert result.name == "RedSquare"
    assert result.age == 1
    logger.info(f"Image input result: {result}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
