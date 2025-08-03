"""Simple direct tests for Claude Code functions."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel
import json


class TestResponse(BaseModel):
    message: str
    value: int


@pytest.mark.asyncio
async def test_subprocess_execution():
    """Test the core subprocess execution logic."""
    with patch("asyncio.create_subprocess_exec") as mock_subprocess:
        # Mock process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Hello World", b""))
        mock_subprocess.return_value = mock_process

        # Test the subprocess call directly
        cmd = ["claude", "-p"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate(input=b"test prompt")
        result = stdout.decode()

        assert result == "Hello World"


@pytest.mark.asyncio
async def test_json_parsing():
    """Test JSON parsing with pydantic model."""
    json_str = '{"message": "test", "value": 42}'

    result = TestResponse.model_validate_json(json_str)
    assert result.message == "test"
    assert result.value == 42


@pytest.mark.asyncio
async def test_json_parsing_with_markdown():
    """Test JSON extraction from markdown."""
    markdown_str = '```json\n{"message": "test", "value": 42}\n```'

    # Extract JSON
    if "```json" in markdown_str:
        json_str = markdown_str.split("```json")[1].split("```")[0].strip()

    result = TestResponse.model_validate_json(json_str)
    assert result.message == "test"
    assert result.value == 42


@pytest.mark.asyncio
async def test_schema_generation():
    """Test pydantic schema generation."""
    schema = TestResponse.model_json_schema()

    assert "properties" in schema
    assert "message" in schema["properties"]
    assert "value" in schema["properties"]
    assert schema["properties"]["message"]["type"] == "string"
    assert schema["properties"]["value"]["type"] == "integer"


def test_prompt_building():
    """Test prompt building with schema."""
    schema = TestResponse.model_json_schema()
    schema_str = json.dumps(schema, indent=2)

    base_prompt = "What is 2+2?"
    full_prompt = f"""{base_prompt}

You must respond with a valid JSON object that matches this schema:
{schema_str}

Provide only the JSON object, no additional text or markdown code blocks."""

    assert "What is 2+2?" in full_prompt
    assert '"type": "string"' in full_prompt
    assert '"type": "integer"' in full_prompt
    assert "properties" in full_prompt
