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
    try:
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
    except Exception as e:
        logger.error(f"Error extracting attributes from {path}: {e}")
        return simple_extract_reviewer_attributes_fallback(path, content)

def simple_extract_reviewer_attributes_fallback(file_path: Path, content: str) -> ReviewerDefinition:
    """
    Simple fallback extraction when LLM extraction fails.
    
    Args:
        file_path: Path to the markdown file
        content: Content of the markdown file
        
    Returns:
        A ReviewerDefinition instance
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
    
    return ReviewerDefinition(
        name=name,
        trigger_condition=trigger,
        return_type=return_type,
        file_path=file_path,
        raw_content=content
    )

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
    a_reviewer_definition_from_path
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
