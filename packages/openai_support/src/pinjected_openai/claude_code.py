import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Protocol

import json_repair
from injected_utils import async_cached, sqlite_dict
from loguru import logger as Logger
from pinjected import IProxy, injected, design
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class ClaudeCodeError(Exception):
    """Base exception for Claude Code subprocess errors."""

    pass


class ClaudeCodeTimeoutError(ClaudeCodeError):
    """Exception raised when Claude Code subprocess times out."""

    pass


class ClaudeCodeNotFoundError(ClaudeCodeError):
    """Exception raised when Claude Code command is not found."""

    pass


class StructuredLLM(Protocol):
    async def __call__(
        self, text: str, images=None, response_format: type[BaseModel] | None = None
    ):
        pass


class ClaudeCodeSubprocessProtocol(Protocol):
    async def __call__(
        self,
        prompt: str,
        timeout: float = 120.0,
        **kwargs,
    ) -> str: ...


class ClaudeCommandPathStrProtocol(Protocol):
    def __call__(self) -> str: ...


class ClaudeModelProtocol(Protocol):
    def __call__(self) -> str: ...


@injected(protocol=ClaudeCommandPathStrProtocol)
def claude_command_path_str() -> str:
    """
    Get the path to the claude command as a string.

    This is a required dependency that must be provided.
    Common values:
    - "/usr/local/bin/claude"
    - str(Path.home() / ".claude" / "local" / "claude")
    """
    # Try to auto-detect for default
    claude_cmd = shutil.which("claude")
    if claude_cmd:
        return claude_cmd

    # Check common locations
    possible_paths = [
        Path.home() / ".claude" / "local" / "claude",
        Path("/usr/local/bin/claude"),
        Path("/opt/homebrew/bin/claude"),
    ]

    for path in possible_paths:
        if path.exists() and path.is_file():
            return str(path)

    raise ClaudeCodeNotFoundError(
        "Claude Code command not found. Install with: npm install -g @anthropic-ai/claude-code"
    )


@injected(protocol=ClaudeCodeSubprocessProtocol)
async def a_claude_code_subprocess(
    claude_command_path_str: str,
    claude_model: str,
    logger: Logger,
    /,
    prompt: str,
    timeout: float = 120.0,
    **kwargs,
) -> str:
    """
    Execute Claude Code CLI via subprocess and return raw text response.

    Args:
        claude_command_path_str: Path to claude command (injected)
        claude_model: Model to use - "sonnet" or "opus" (injected)
        logger: Logger instance
        prompt: The text prompt to send to Claude
        timeout: Timeout in seconds for subprocess execution
        **kwargs: Additional arguments (for compatibility)

    Returns:
        Raw text response from Claude
    """

    # Use injected command path
    claude_cmd = claude_command_path_str

    # Verify the command exists
    if not Path(claude_cmd).exists():
        raise ClaudeCodeNotFoundError(
            f"Claude command not found at specified path: {claude_cmd}"
        )

    cmd = [claude_cmd, "-p", "--model", claude_model]

    logger.info(
        f"Executing Claude Code with prompt length: {len(prompt)}, model: {claude_model}, using command: {claude_cmd}"
    )

    try:
        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Send prompt and get response
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=prompt.encode()), timeout=timeout
        )

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(
                f"Claude Code failed with return code {process.returncode}: {error_msg}"
            )
            raise ClaudeCodeError(f"Claude Code failed: {error_msg}")

        # Decode response
        response_text = stdout.decode()
        logger.debug(f"Raw response length: {len(response_text)}")

        # Return raw text response
        return response_text

    except asyncio.TimeoutError:
        logger.error(f"Claude Code timed out after {timeout} seconds")
        raise ClaudeCodeTimeoutError(f"Claude Code timed out after {timeout} seconds")
    except FileNotFoundError as e:
        logger.error(
            "Claude Code command not found. Make sure @anthropic-ai/claude-code is installed"
        )
        raise ClaudeCodeNotFoundError(
            "Claude Code command not found. Install with: npm install -g @anthropic-ai/claude-code"
        ) from e


class ClaudeCodeStructuredProtocol(Protocol):
    async def __call__(
        self,
        prompt: str,
        response_format: type[BaseModel],
        **kwargs,
    ) -> BaseModel: ...


@injected(protocol=ClaudeCodeStructuredProtocol)
async def a_claude_code_structured(  # noqa: PINJ045
    a_claude_code_subprocess: ClaudeCodeSubprocessProtocol,
    logger: Logger,
    /,
    prompt: str,
    response_format: type[BaseModel],
    **kwargs,
) -> BaseModel:
    """
    Execute Claude Code and parse structured response.

    Args:
        a_claude_code_subprocess: Subprocess executor
        logger: Logger instance
        prompt: The text prompt
        response_format: Pydantic model for response validation
        **kwargs: Additional arguments

    Returns:
        Validated pydantic model instance
    """
    # Build prompt with JSON schema
    schema = response_format.model_json_schema()
    schema_str = json.dumps(schema, indent=2)
    full_prompt = f"""{prompt}

You must respond with a valid JSON object that matches this schema:
{schema_str}

Provide only the JSON object, no additional text or markdown code blocks."""

    # Get response
    response_text = await a_claude_code_subprocess(prompt=full_prompt, **kwargs)

    # Parse and validate response
    try:
        # Try to extract JSON from the content
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text

        # Parse and validate
        return response_format.model_validate_json(json_str)

    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Failed to parse JSON response: {e}")
        # Try json_repair as fallback
        try:
            repaired = json_repair.loads(response_text)
            return response_format.model_validate(repaired)
        except Exception as repair_error:
            logger.error(f"JSON repair also failed: {repair_error}")
            raise ClaudeCodeError(f"Failed to parse structured response: {e}")


@injected(protocol=StructuredLLM)
@retry(
    retry=retry_if_exception_type(ClaudeCodeTimeoutError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
)
async def a_sllm_claude_code(  # noqa: PINJ045
    a_claude_code_subprocess: ClaudeCodeSubprocessProtocol,
    a_claude_code_structured: ClaudeCodeStructuredProtocol,
    logger: Logger,
    /,
    text: str,
    images=None,
    response_format: type[BaseModel] | None = None,
    max_tokens: int = 8192,
) -> Any:
    """
    StructuredLLM implementation using Claude Code subprocess.
    Includes retry logic for timeouts.

    Args:
        a_claude_code_subprocess: Subprocess executor for plain text
        a_claude_code_structured: Structured response handler
        logger: Logger instance
        text: The prompt text
        images: Images (currently not supported)
        response_format: Optional pydantic BaseModel for structured output
        max_tokens: Maximum tokens (currently not used by subprocess)

    Returns:
        Response from Claude (structured or plain text)
    """
    if images is not None:
        logger.warning(
            "Images are not currently supported in Claude Code subprocess implementation"
        )

    with logger.contextualize(tag="claude_code_sllm"):
        logger.info(f"Calling Claude Code with prompt length: {len(text)}")

        try:
            if response_format is not None:
                # Use structured handler
                result = await a_claude_code_structured(
                    prompt=text,
                    response_format=response_format,
                )
            else:
                # Use plain text handler
                result = await a_claude_code_subprocess(prompt=text)

            logger.success("Claude Code call completed successfully")
            return result

        except ClaudeCodeNotFoundError as e:
            logger.error(f"Claude Code not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling Claude Code: {e}")
            raise


@injected(protocol=ClaudeModelProtocol)
def claude_model() -> str:
    """Get the Claude model to use. Default is 'opus'."""
    return "opus"


# Test instances
class SimpleResponse(BaseModel):
    answer: str
    confidence: float


test_claude_code_plain: IProxy[StructuredLLM] = a_sllm_claude_code(
    text="What is the capital of Japan? Answer in one word.",
)

test_claude_code_structured: IProxy[StructuredLLM] = a_sllm_claude_code(
    text="What is the capital of Japan? Provide your answer with a confidence score.",
    response_format=SimpleResponse,
)

# Cached version for production use
a_cached_sllm_claude_code: IProxy[StructuredLLM] = async_cached(
    sqlite_dict(injected("cache_root_path") / "claude_code.sqlite")
)(a_sllm_claude_code)

__design__ = design(
    claude_command_path_str=str(Path("~/.claude/local/claude").expanduser().absolute()),
    claude_model="opus",  # Default model
)
