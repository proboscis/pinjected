from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Literal

@dataclass
class ReviewerDefinition:
    """Represents a reviewer definition loaded from a markdown file."""
    name: str
    trigger_condition: str  # When to trigger (on commit, etc.)
    return_type: str
    file_path: Path  # Original markdown file path
    raw_content: str  # Original markdown content
    
    @classmethod
    def from_markdown(cls, file_path: Path, content: str, llm_extractor) -> "ReviewerDefinition":
        """
        Create a ReviewerDefinition from markdown content using an LLM extractor.
        
        Args:
            file_path: Path to the markdown file
            content: Content of the markdown file
            llm_extractor: Function that extracts attributes from markdown
            
        Returns:
            A ReviewerDefinition instance
        """
        attributes = llm_extractor(content)
        return cls(
            name=attributes.get("Name", "Unnamed Reviewer"),
            trigger_condition=attributes.get("When to trigger", "manual"),
            return_type=attributes.get("Return Type", "None"),
            file_path=file_path,
            raw_content=content
        )
