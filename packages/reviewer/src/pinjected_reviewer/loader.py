from pathlib import Path
from typing import List, Dict, Optional, Type

from pinjected import instance, injected
from loguru import logger
from pydantic import BaseModel

from pinjected_reviewer.reviewer_def import ReviewerDefinition, ReviewerAttributes

@injected
async def a_sllm_for_markdown_extraction(
    logger,
    /,
    content: str,
    response_format: Type[BaseModel] = None,
    structured_llm = None
) -> BaseModel:
    """
    Extracts attributes from markdown content using a structured LLM.
    
    Args:
        logger: Logger instance
        content: Markdown content to extract attributes from
        response_format: Pydantic model class for the response
        structured_llm: Optional structured LLM to use
        
    Returns:
        Instance of the response_format model with extracted attributes
    """
    if structured_llm is None:
        logger.warning("No structured LLM available, using simple parsing fallback")
        return simple_extract_reviewer_attributes(content, response_format)
    
    prompt = f"""
    Extract the following attributes from this markdown reviewer definition:
    - Name: The name of the reviewer
    - When_to_trigger: When this reviewer should be triggered (e.g., on commit)
    - Return_Type: The return type of this reviewer
    
    Markdown content:
    {content}
    """
    
    return await structured_llm(text=prompt, response_format=response_format)

def simple_extract_reviewer_attributes(content: str, model_class: Type[BaseModel]) -> BaseModel:
    """
    Simple fallback extraction when no LLM is available.
    
    Args:
        content: Markdown content to extract attributes from
        model_class: Pydantic model class for the response
        
    Returns:
        Instance of the model_class with extracted attributes
    """
    import re
    
    name_match = re.search(r"# ([^\n]+)", content)
    name = name_match.group(1).strip() if name_match else "Unnamed Reviewer"
    
    trigger_match = re.search(r"(?i)when to trigger:?\s*([^\n]+)", content)
    if not trigger_match:
        trigger_match = re.search(r"(?i)^\s*(on\s+\w+)\s*$", content, re.MULTILINE)
    trigger = trigger_match.group(1).strip() if trigger_match else "manual"
    
    return_match = re.search(r"(?i)return type:?\s*([^\n]+)", content)
    if not return_match:
        return_match = re.search(r"(?i)^\s*(\w+)\s*$", content, re.MULTILINE)
    return_type = return_match.group(1).strip() if return_match else "None"
    
    return model_class(
        Name=name,
        When_to_trigger=trigger,
        Return_Type=return_type
    )

def find_reviewer_markdown_files(repo_root: Path) -> List[Path]:
    """
    Find all markdown files in the .reviewers directory.
    
    Args:
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
    a_sllm_for_markdown_extraction
) -> List[ReviewerDefinition]:
    """
    Load all reviewer definitions from markdown files.
    
    Args:
        repo_root: Root directory of the repository
        a_sllm_for_markdown_extraction: Function to extract attributes from markdown
        
    Returns:
        List of ReviewerDefinition instances
    """
    markdown_files = find_reviewer_markdown_files(repo_root)
    definitions = []
    
    for file_path in markdown_files:
        try:
            content = file_path.read_text()
            definition = await ReviewerDefinition.from_markdown(
                file_path=file_path,
                content=content,
                a_sllm_for_markdown_extraction=a_sllm_for_markdown_extraction
            )
            definitions.append(definition)
            logger.info(f"Loaded reviewer definition: {definition.name} from {file_path.name}")
        except Exception as e:
            logger.error(f"Error loading reviewer definition from {file_path}: {e}")
    
    return definitions
