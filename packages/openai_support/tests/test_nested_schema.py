"""Test nested schema handling for OpenAI structured output."""

import pytest
from pinjected import design, injected
from pinjected.test import injected_pytest
from pydantic import BaseModel
from typing import Optional, List
from pinjected_openai.direct_openai import ensure_strict_schema
from packages.openai_support.conftest import apikey_skip_if_needed

apikey_skip_if_needed()


class ScoreWithReasoningV2(BaseModel):
    """Represents a relevance score with explanation."""

    symbol: str  # Symbol identifier
    score: float  # 0-1 relevance score
    reasoning: str  # Explanation for the score


class SymbolAssessmentsV2(BaseModel):
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


def verify_nested_schema_has_additional_properties_false():
    """Verify that nested schemas have additionalProperties: false set recursively."""

    # Get the schema for the nested model
    schema = SymbolAssessmentsV2.model_json_schema()

    # Apply our fix
    fixed_schema = ensure_strict_schema(schema)

    # Check the main object has additionalProperties: false
    assert fixed_schema.get("additionalProperties") is False, (
        "Main schema object should have additionalProperties: false"
    )

    # Check nested objects in properties
    if "properties" in fixed_schema and "assessments" in fixed_schema["properties"]:
        assessments_schema = fixed_schema["properties"]["assessments"]

        # Check if there's an items schema for the array
        if "items" in assessments_schema:
            item_schema = assessments_schema["items"]

            # If it's a direct object definition
            if "type" in item_schema and item_schema["type"] == "object":
                assert item_schema.get("additionalProperties") is False, (
                    "Nested array item object should have additionalProperties: false"
                )

            # If it references a definition
            elif "$ref" in item_schema:
                # Check the referenced definition
                ref_path = item_schema["$ref"]
                if ref_path.startswith("#/$defs/"):
                    def_name = ref_path.replace("#/$defs/", "")
                    if "$defs" in fixed_schema and def_name in fixed_schema["$defs"]:
                        def_schema = fixed_schema["$defs"][def_name]
                        assert def_schema.get("additionalProperties") is False, (
                            f"Referenced definition {def_name} should have additionalProperties: false"
                        )

    # Check all definitions have additionalProperties: false
    if "$defs" in fixed_schema:
        for def_name, def_schema in fixed_schema["$defs"].items():
            if "type" in def_schema and def_schema["type"] == "object":
                assert def_schema.get("additionalProperties") is False, (
                    f"Definition {def_name} should have additionalProperties: false"
                )

    print("✅ All nested schemas have additionalProperties: false")


@pytest.mark.asyncio
@injected_pytest(
    design(
        openai_config=injected("openai_config__personal"),
        openai_api_key=injected("openai_config__personal")["api_key"],
        openai_organization=None,
    )
)
async def test_nested_schema_with_openai_api(
    a_sllm_openai,
    logger,
    /,
):
    """Test that nested schemas work with OpenAI API without errors."""

    logger.info("\n" + "=" * 80)
    logger.info("TESTING NESTED SCHEMA WITH OPENAI API")
    logger.info("=" * 80)

    # Test with the problematic nested schema
    logger.info("\nTesting SymbolAssessmentsV2 with nested ScoreWithReasoningV2...")

    try:
        result = await a_sllm_openai(
            text=(
                "Assess the relevance of these symbols to machine learning:\n"
                "- numpy: numerical computing library\n"
                "- pandas: data manipulation library\n"
                "Give each a score from 0-1 and reasoning."
            ),
            model="gpt-4o",
            response_format=SymbolAssessmentsV2,
            max_tokens=500,
        )

        assert isinstance(result, SymbolAssessmentsV2), (
            f"Expected SymbolAssessmentsV2, got {type(result)}"
        )
        assert len(result.assessments) > 0, "Should have at least one assessment"

        for assessment in result.assessments:
            assert isinstance(assessment, ScoreWithReasoningV2)
            assert 0 <= assessment.score <= 1, (
                f"Score should be 0-1, got {assessment.score}"
            )
            assert assessment.symbol, "Symbol should not be empty"
            assert assessment.reasoning, "Reasoning should not be empty"

        logger.success(
            f"✅ Nested schema works! Got {len(result.assessments)} assessments"
        )
        for assessment in result.assessments:
            logger.info(
                f"  - {assessment.symbol}: {assessment.score:.2f} - {assessment.reasoning[:50]}..."
            )

    except Exception as e:
        if "additionalProperties" in str(e):
            logger.error(f"❌ Schema error (additionalProperties issue): {e}")
            raise
        else:
            logger.error(f"❌ Unexpected error: {e}")
            raise

    logger.info("\n" + "=" * 80)
    logger.info("NESTED SCHEMA TEST COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)


if __name__ == "__main__":
    # Run the schema verification first
    verify_nested_schema_has_additional_properties_false()

    # Then run the API test
    pytest.main(
        [__file__, "-v", "-s", "-x", "-k", "test_nested_schema_with_openai_api"]
    )
