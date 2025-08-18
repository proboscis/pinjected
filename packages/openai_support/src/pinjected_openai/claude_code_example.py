"""Example usage of Claude Code StructuredLLM implementation.

Note: The claude_command_path_str dependency is required and must be provided.
It will attempt to auto-detect claude in common locations, but you can override it.
"""
from typing import Protocol
from pinjected import design, injected
from pinjected_openai.claude_code import a_cached_sllm_claude_code
from pydantic import BaseModel


class CityInfo(BaseModel):
    name: str
    country: str
    population: int
    is_capital: bool


async def example_usage():
    """Example of using Claude Code via subprocess."""
    # Create a design with the cached Claude Code implementation
    app_design = design(
        structured_llm=a_cached_sllm_claude_code
    )
    
    # Get the structured_llm from the design
    structured_llm = await app_design.to_resolver().aresolve("structured_llm")
    
    # Use it for plain text
    plain_result = await structured_llm(text="What is the capital of Japan?")
    print(f"Plain text result: {plain_result}")
    
    # Use it for structured output
    structured_result = await structured_llm(
        text="Tell me about Tokyo",
        response_format=CityInfo
    )
    print(f"Structured result: {structured_result}")
    print(f"City: {structured_result.name}, Population: {structured_result.population}")


class MyClaudeCommandProtocol(Protocol):
    def __call__(self) -> str: ...


# Define a custom claude command path at module level
@injected(protocol=MyClaudeCommandProtocol)
def my_claude_command() -> str:
    """Custom claude command path for example."""
    # Return your custom path here
    # For example: return "/opt/homebrew/bin/claude"
    return "/Users/myuser/.local/bin/claude"


async def example_with_custom_path():
    """Example using a custom claude command path."""
    # Create a design that overrides the claude_command_path_str
    app_design = design(
        claude_command_path_str=my_claude_command,
        structured_llm=a_cached_sllm_claude_code
    )
    
    # Get the structured_llm from the design
    structured_llm = await app_design.to_resolver().aresolve("structured_llm")
    
    # Use it normally - it will use your custom path
    result = await structured_llm(text="What is 2 + 2?")
    print(f"Result with custom claude path: {result}")


async def run_all_examples():
    """Run all examples. Call with: python -m pinjected run pinjected_openai.claude_code_example.run_all_examples"""
    print("Example 1: Default auto-detection")
    try:
        await example_usage()
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n\nExample 2: Custom claude path")
    try:
        await example_with_custom_path()
    except Exception as e:
        print(f"Error: {e}")


# To run these examples, use:
# python -m pinjected run pinjected_openai.claude_code_example.example_usage
# python -m pinjected run pinjected_openai.claude_code_example.example_with_custom_path
# python -m pinjected run pinjected_openai.claude_code_example.run_all_examples
