from pathlib import Path
from typing import List, Dict, Optional, Type

from pinjected import instance, injected
from loguru import logger
from pydantic import BaseModel
from pinjected_openai.openrouter.instances import StructuredLLM

from pinjected_reviewer.reviewer_def import ReviewerDefinition, ReviewerAttributes


@injected
async def a_reviewer_definition_from_path(
        a_structured_llm_for_markdown_extraction: StructuredLLM,
        logger,
        /,
        path: Path
) -> ReviewerDefinition:
    """
    Create a ReviewerDefinition from a markdown file path using a structured LLM.
    
    Args:
        a_structured_llm_for_markdown_extraction: Structured LLM for extracting attributes from markdown
        logger: Logger instance
        path: Path to the markdown file
        
    Returns:
        A ReviewerDefinition instance
    """
    content = path.read_text()

    prompt = f"""
    Extract the following attributes from this markdown reviewer definition:
    - Name: The name of the reviewer
    - When_to_trigger: When this reviewer should be triggered (e.g., on commit)
    - Return_Type: The return type of this reviewer
    
    Markdown content:
    {content}
    """

    attributes = await a_structured_llm_for_markdown_extraction(
        text=prompt,
        response_format=ReviewerAttributes
    )

    return ReviewerDefinition(
        name=attributes.Name,
        trigger_condition=attributes.When_to_trigger,
        return_type=attributes.Return_Type,
        file_path=path,
        raw_content=content
    )


@injected
def find_reviewer_markdown_files(
        logger,
        /,
        repo_root: Path
) -> List[Path]:
    """
    Find all markdown files in the .reviewers directory.
    
    Args:
        logger: Logger instance
        repo_root: The root directory of the repository
        
    Returns:
        List of paths to reviewer markdown files
    """
    reviewers_dir = repo_root / ".reviewers"
    if not reviewers_dir.exists():
        logger.warning(f"Reviewers directory not found: {reviewers_dir}")
        return []

    markdown_files = list(reviewers_dir.glob("*.md"))
    logger.info(f"Found {len(markdown_files)} reviewer definition files in {reviewers_dir}")
    return markdown_files


@instance
async def reviewer_definitions(
        repo_root: Path,
        a_reviewer_definition_from_path,
        find_reviewer_markdown_files
) -> List[ReviewerDefinition]:
    """
    Load all reviewer definitions from markdown files.
    
    Args:
        repo_root: Root directory of the repository
        a_reviewer_definition_from_path: Function to create a ReviewerDefinition from a file path
        
    Returns:
        List of ReviewerDefinition instances
    """
    markdown_files = find_reviewer_markdown_files(repo_root)
    definitions = []

    for file_path in markdown_files:
        try:
            definition = await a_reviewer_definition_from_path(path=file_path)
            definitions.append(definition)
            logger.info(f"Loaded reviewer definition: {definition.name} from {file_path.name}")
        except Exception as e:
            logger.error(f"Error loading reviewer definition from {file_path}: {e}")

    return definitions
