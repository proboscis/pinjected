from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Literal

from pydantic import BaseModel, Field

class ReviewerAttributes(BaseModel):
    """Represents attributes extracted from a reviewer markdown file. Used for LLM based extraction."""
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
