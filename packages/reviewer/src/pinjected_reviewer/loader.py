from pathlib import Path
from typing import List, Dict, Optional, Callable

from pinjected import instance, injected, Injected
from loguru import logger

from pinjected_reviewer.reviewer_def import ReviewerDefinition

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
def llm_markdown_extractor(openai_client = None, anthropic_client = None) -> Callable[[str], Dict[str, str]]:
    """
    Creates a function that extracts attributes from markdown using an LLM.
    
    Args:
        openai_client: Optional OpenAI client
        anthropic_client: Optional Anthropic client
        
    Returns:
        Function that extracts attributes from markdown
    """
    if openai_client is not None:
        from pinjected_openai.clients import AsyncOpenAI
        
        async def extract_with_openai(content: str) -> Dict[str, str]:
            prompt = f"""
            Extract the following attributes from this markdown reviewer definition:
            - Name: The name of the reviewer
            - When to trigger: When this reviewer should be triggered (e.g., on commit)
            - Return Type: The return type of this reviewer
            
            Format your response as a JSON object with these keys.
            
            Markdown content:
            {content}
            """
            
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
        
        def extract(content: str) -> Dict[str, str]:
            import asyncio
            return asyncio.run(extract_with_openai(content))
            
        return extract
    
    elif anthropic_client is not None:
        pass
    
    logger.warning("No LLM client available, using simple parsing fallback")
    
    def simple_extract(content: str) -> Dict[str, str]:
        import re
        result = {}
        
        name_match = re.search(r"# ([^\n]+)", content)
        if name_match:
            result["Name"] = name_match.group(1).strip()
        
        trigger_match = re.search(r"(?i)when to trigger:?\s*([^\n]+)", content)
        if trigger_match:
            result["When to trigger"] = trigger_match.group(1).strip()
        
        return_match = re.search(r"(?i)return type:?\s*([^\n]+)", content)
        if return_match:
            result["Return Type"] = return_match.group(1).strip()
            
        return result
    
    return simple_extract

@instance
def reviewer_definitions(
    repo_root: Path,
    llm_markdown_extractor: Callable[[str], Dict[str, str]]
) -> List[ReviewerDefinition]:
    """
    Load all reviewer definitions from markdown files.
    
    Args:
        repo_root: Root directory of the repository
        llm_markdown_extractor: Function to extract attributes from markdown
        
    Returns:
        List of ReviewerDefinition instances
    """
    markdown_files = find_reviewer_markdown_files(repo_root)
    definitions = []
    
    for file_path in markdown_files:
        try:
            content = file_path.read_text()
            definition = ReviewerDefinition.from_markdown(
                file_path=file_path,
                content=content,
                llm_extractor=llm_markdown_extractor
            )
            definitions.append(definition)
            logger.info(f"Loaded reviewer definition: {definition.name} from {file_path.name}")
        except Exception as e:
            logger.error(f"Error loading reviewer definition from {file_path}: {e}")
    
    return definitions
