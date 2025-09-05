"""Test that demonstrates the nested schema additionalProperties fix."""

import pytest
import json
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel
from typing import Optional, List
from pinjected_openai.direct_openai import ensure_strict_schema
from packages.openai_support.conftest import apikey_skip_if_needed

apikey_skip_if_needed()


class ScoreWithReasoningV2(BaseModel):
    """Represents a relevance score with explanation - exact class from user's error report."""

    symbol: str  # Symbol identifier
    score: float  # 0-1 relevance score
    reasoning: str  # Explanation for the score


class SymbolAssessmentsV2(BaseModel):
    """Exact class from user's error report that was failing."""

    assessments: list[ScoreWithReasoningV2]

    def get(self, symbol: str) -> Optional[ScoreWithReasoningV2]:
        """Get assessment for a specific symbol."""
        for assessment in self.assessments:
            if assessment.symbol == symbol:
                return assessment
        return None

    def contains(self, symbol: str) -> bool:
        """Check if symbol has an assessment."""
        return self.get(symbol) is not None

    def symbols(self) -> List[str]:
        """Get list of all symbols."""
        return [a.symbol for a in self.assessments]

    def items(self) -> List[tuple[str, ScoreWithReasoningV2]]:
        """Get list of (symbol, assessment) tuples."""
        return [(a.symbol, a) for a in self.assessments]

    def __len__(self) -> int:
        return len(self.assessments)


def demonstrate_schema_problem_without_fix():
    """
    This demonstrates that without the fix, the schema would be missing
    additionalProperties: false in nested objects, causing the OpenAI API error:

    'Invalid schema for response_format 'SymbolAssessmentsV2': In context=(),
    'additionalProperties' is required to be supplied and to be false.'
    """
    # Get the raw schema without our fix
    raw_schema = SymbolAssessmentsV2.model_json_schema()

    # Check that nested objects don't have additionalProperties by default
    print("\nRaw schema (before fix):")
    print(json.dumps(raw_schema, indent=2))

    # The raw schema from pydantic doesn't set additionalProperties: false recursively
    # This is what would cause the OpenAI error
    if "$defs" in raw_schema:
        for def_name, def_schema in raw_schema["$defs"].items():
            if def_name == "ScoreWithReasoningV2":
                # This assertion shows the problem - no additionalProperties: false
                assert (
                    "additionalProperties" not in def_schema
                    or def_schema.get("additionalProperties") is not False
                ), (
                    "Before fix, nested schemas should NOT have additionalProperties: false"
                )
                print(
                    f"\n❌ PROBLEM: {def_name} is missing 'additionalProperties: false'"
                )
                print(
                    f"   This would cause OpenAI error: 'additionalProperties' is required to be supplied and to be false"
                )


def demonstrate_schema_solution_with_fix():
    """
    This demonstrates that with our fix, all nested objects have
    additionalProperties: false, which prevents the OpenAI API error.
    """
    # Get the raw schema
    raw_schema = SymbolAssessmentsV2.model_json_schema()

    # Apply our fix
    fixed_schema = ensure_strict_schema(raw_schema)

    print("\nFixed schema (after applying ensure_strict_schema):")
    print(json.dumps(fixed_schema, indent=2))

    # Verify the fix worked - all objects should have additionalProperties: false
    assert fixed_schema.get("additionalProperties") is False, (
        "Root schema should have additionalProperties: false"
    )

    # Check nested definitions
    if "$defs" in fixed_schema:
        for def_name, def_schema in fixed_schema["$defs"].items():
            if "type" in def_schema and def_schema["type"] == "object":
                assert def_schema.get("additionalProperties") is False, (
                    f"After fix, {def_name} should have additionalProperties: false"
                )
                print(f"\n✅ FIXED: {def_name} now has 'additionalProperties: false'")

    print("\n✅ All nested schemas now have additionalProperties: false")
    print("   This prevents the OpenAI API error!")


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_openai_api_with_nested_schema(
    a_sllm_openai,
    logger,
    /,
):
    """
    Integration test that would have failed with the original error:
    'Invalid schema for response_format 'SymbolAssessmentsV2': In context=(),
    'additionalProperties' is required to be supplied and to be false.'

    But now succeeds because we apply ensure_strict_schema() in a_sllm_openai.
    """
    logger.info("\n" + "=" * 80)
    logger.info("REPRODUCING USER'S EXACT ERROR SCENARIO")
    logger.info("=" * 80)

    logger.info("\nTesting the exact SymbolAssessmentsV2 class that was failing...")
    logger.info(
        "Error was: 'additionalProperties' is required to be supplied and to be false"
    )

    # This is the exact call that would have failed before the fix
    try:
        result = await a_sllm_openai(
            text=(
                "Assess the relevance of these symbols to machine learning:\n"
                "- numpy: numerical computing library\n"
                "- pandas: data manipulation library\n"
                "Give each a score from 0-1 and reasoning."
            ),
            model="gpt-4o",
            response_format=SymbolAssessmentsV2,  # This was failing!
            max_tokens=500,
        )

        # Verify the response is valid
        assert isinstance(result, SymbolAssessmentsV2), (
            f"Expected SymbolAssessmentsV2, got {type(result)}"
        )
        assert len(result.assessments) > 0, "Should have assessments"

        logger.success("✅ SUCCESS! The nested schema error is fixed!")
        logger.info(f"   Got {len(result.assessments)} assessments back")
        logger.info("   Before the fix, this would have failed with:")
        logger.info(
            "   'additionalProperties' is required to be supplied and to be false"
        )

        # Show that the methods work too
        assert result.contains("numpy") or result.contains("pandas"), (
            "Should contain assessed symbols"
        )
        symbols = result.symbols()
        logger.info(f"   Symbols assessed: {symbols}")

    except Exception as e:
        if "additionalProperties" in str(e):
            logger.error("❌ THE ORIGINAL ERROR STILL EXISTS!")
            logger.error(f"   Error: {e}")
            logger.error("   The fix didn't work properly")
            raise
        else:
            logger.error(f"❌ Different error: {e}")
            raise

    logger.info("\n" + "=" * 80)
    logger.info(
        "FIX VERIFIED: The nested schema additionalProperties issue is resolved!"
    )
    logger.info("=" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("DEMONSTRATING THE NESTED SCHEMA FIX")
    print("=" * 80)

    # Show the problem
    print("\n1. First, showing the PROBLEM (what would cause the error):")
    demonstrate_schema_problem_without_fix()

    # Show the solution
    print("\n2. Now, showing the SOLUTION (how our fix resolves it):")
    demonstrate_schema_solution_with_fix()

    # Run the integration test
    print("\n3. Running integration test with OpenAI API:")
    pytest.main(
        [__file__, "-v", "-s", "-x", "-k", "test_openai_api_with_nested_schema"]
    )
