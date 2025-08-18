"""Test JSON parsing directly."""

import pytest
from pinjected.test import injected_pytest
from pinjected_openai.openrouter.util import (
    extract_json_from_markdown,
    parse_json_response,
)
from pydantic import BaseModel
from loguru import logger


class SimpleModel(BaseModel):
    """Simple model for testing."""

    name: str
    age: int


@injected_pytest
def test_extract_json_from_markdown():
    """Test JSON extraction from markdown."""

    # Test with json code block
    data = '```json\n{"name": "John", "age": 30}\n```'
    result = extract_json_from_markdown(data)
    logger.info(f"Extracted from markdown: {result!r}")
    assert result == '{"name": "John", "age": 30}'

    # Test without code block
    data = '{"name": "Jane", "age": 25}'
    result = extract_json_from_markdown(data)
    assert result == '{"name": "Jane", "age": 25}'

    # Test with text before and after
    data = 'Here is the JSON:\n```json\n{"name": "Bob", "age": 35}\n```\nThat\'s all!'
    result = extract_json_from_markdown(data)
    assert result == '{"name": "Bob", "age": 35}'

    # Test without json marker
    data = '```\n{"name": "Alice", "age": 40}\n```'
    result = extract_json_from_markdown(data)
    assert result == '{"name": "Alice", "age": 40}'


@pytest.mark.asyncio
@injected_pytest
async def test_parse_json_response(
    a_structured_llm_for_json_fix,
    logger,
    /,
):
    """Test parse_json_response function."""

    # Test with valid JSON in markdown
    data = '```json\n{"name": "John", "age": 30}\n```'
    result = await parse_json_response(
        data=data,
        response_format=SimpleModel,
        logger=logger,
        a_structured_llm_for_json_fix=a_structured_llm_for_json_fix,
        prompt="Test prompt",
    )
    logger.info(f"Parsed result type: {type(result)}")
    logger.info(f"Parsed result: {result}")
    assert isinstance(result, SimpleModel)
    assert result.name == "John"
    assert result.age == 30

    # Test with plain JSON
    data = '{"name": "Jane", "age": 25}'
    result = await parse_json_response(
        data=data,
        response_format=SimpleModel,
        logger=logger,
        a_structured_llm_for_json_fix=a_structured_llm_for_json_fix,
        prompt="Test prompt",
    )
    assert isinstance(result, SimpleModel)
    assert result.name == "Jane"
    assert result.age == 25


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-x"])
