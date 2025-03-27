from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Literal

from pydantic import BaseModel, Field

class ReviewerAttributes(BaseModel):
    """Represents attributes extracted from a reviewer markdown file."""
    Name: str = Field(..., description="The name of the reviewer")
    When_to_trigger: str = Field(..., description="When this reviewer should be triggered (e.g., on commit)")
    Return_Type: str = Field(..., description="The return type of this reviewer")

@dataclass
class ReviewerDefinition:
    """Represents a reviewer definition loaded from a markdown file."""
    name: str
    trigger_condition: str  # When to trigger (on commit, etc.)
    return_type: str
    file_path: Path  # Original markdown file path
    raw_content: str  # Original markdown content
    
    @classmethod
    async def from_markdown(cls, file_path: Path, content: str, a_sllm_for_markdown_extraction) -> "ReviewerDefinition":
        """
        Create a ReviewerDefinition from markdown content using an LLM extractor.
        
        Args:
            file_path: Path to the markdown file
            content: Content of the markdown file
            a_sllm_for_markdown_extraction: Function that extracts attributes from markdown
            
        Returns:
            A ReviewerDefinition instance
        """
        attributes = await a_sllm_for_markdown_extraction(content, response_format=ReviewerAttributes)
        return cls(
            name=attributes.Name,
            trigger_condition=attributes.When_to_trigger,
            return_type=attributes.Return_Type,
            file_path=file_path,
            raw_content=content
        )
