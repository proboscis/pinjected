import asyncio
import importlib.resources
import sys
from pathlib import Path
from typing import Callable, Awaitable

from loguru import logger
from tqdm import tqdm

from pinjected import injected, instance
from pinjected_openai.openrouter.instances import StructuredLLM
from pinjected_reviewer.schema.types import Approved, FileDiff, Review, GitInfo
from pinjected_reviewer.utils import check_if_file_should_be_ignored


def load_review_material(filename: str) -> str:
    """
    Loads a review material file from various possible locations.

    This function tries multiple approaches to find and load the review material:
    1. First tries package resources (importlib.resources)
    2. Then tries relative to the current file
    3. Then tries common locations like current directory

    Args:
        filename: The name of the file to load (e.g., "how_to_use_pinjected.md")

    Returns:
        str: The content of the file
    """
    # Try importlib.resources first (works when installed as a package)
    try:
        if sys.version_info >= (3, 9):
            # Python 3.9+ approach
            with importlib.resources.files('review_materials').joinpath(filename).open('r') as f:
                return f.read()
        else:
            # Older Python approach
            return importlib.resources.read_text('review_materials', filename)
    except (ImportError, FileNotFoundError, ModuleNotFoundError, ValueError) as e:
        logger.debug(f"Could not load review material via importlib.resources: {e}")

    # Try relative to this file
    try:
        guide_path = Path(__file__).parent.parent / 'review_materials' / filename
        if guide_path.exists():
            return guide_path.read_text()
    except Exception as e:
        logger.debug(f"Could not load review material from relative path: {e}")

    # Try other common locations
    for check_path in [
        Path.cwd() / 'review_materials' / filename,
        Path.cwd() / 'src' / 'review_materials' / filename,
        Path.home() / '.pinjected-reviewer' / 'review_materials' / filename
    ]:
        try:
            if check_path.exists():
                logger.debug(f"Found review material at {check_path}")
                return check_path.read_text()
        except Exception as e:
            continue

    # Nothing worked, return a default message
    logger.error(f"Could not find review material: {filename}")
    return f"# Pinjected Guide\nNo guide found for {filename}. Please check installation."


@injected
async def a_extract_approved(
        a_sllm_for_approval_extraction: StructuredLLM,
        /,
        text: str
) -> Approved:
    prompt = f"""
Please read the following text and extract if the answer of a text is `approved` or `not approved`.
{text}

The answer must be true if it is approved and false if it is not approved.
"""
    return await a_sllm_for_approval_extraction(prompt, response_format=Approved)


@instance
async def pinjected_guide_md():
    return load_review_material('how_to_use_pinjected.md')


@injected
async def a_review_python_diff(
        a_sllm_for_commit_review: StructuredLLM,
        a_extract_approved: Callable[[str], Awaitable[Approved]],
        pinjected_guide_md: str,
        /,
        diff: FileDiff
):
    assert diff.filename.name.endswith('.py'), "Not a Python file"

    # Extract file content from diff to check for ignore comments
    # This is a simple approach to handle the common case where an ignore comment exists in the file
    # It won't catch all cases (like if the ignore comment is removed in the diff)
    # But it's sufficient for most use cases
    file_content = diff.diff
    if diff.is_deleted:
        return Review(
            name=f"Pinjected Coding Style for {diff.filename}",
            review_text=f"File {diff.filename} is deleted. Skipping review.",
            approved=True
        )

    # Check if file should be ignored using our robust function
    if check_if_file_should_be_ignored(file_content, diff.filename):
        logger.info(f"Ignoring file {diff.filename} due to pinjected-reviewer ignore/skip comment")
        return Review(
            name=f"Pinjected Coding Style for {diff.filename}",
            review_text=f"File contains a pinjected-reviewer ignore/skip comment. Skipping review.",
            approved=True
        )

    prompt = f"""
Read the following guide to understand how to use Pinjected in your code:
{pinjected_guide_md}
Now, please review the following Python code changes.
The review must point out any violations of the guide, with clear reasons with examples.
If any violations are found, you must not approve the changes.
Even tiny violation like missing prefix in naming conventions are not allowed.
However, missing space or adding space can be ignored if it is not a violation of the guide.
Beware @injcted functions must not be directly called unless it is trying to make IProxy object.
@injected function must be requested as a dependency in @instance/@injected function to have dependency resolved.
Note the following:
- if not used, instance, injected, design, and other decorators does not need to be imported.
- Commenting out is not part of the review.
- White spaces are not part of the review.
- Anything not relevant to pinjected is not part of the review.
- discourage instances(), providers(), classes() use for making Design object, since they are deprecated. Suggest using design() instead.
- if you find bind_provider() call, it is deprecated and violation

```diff
{diff.diff}
```
The review must include the final approval status as `approved` or `rejected`.
Example:
Final approval status: approved
"""
    resp: str = await a_sllm_for_commit_review(prompt)
    approved = await a_extract_approved(resp)
    return Review(name=f"Pinjected Coding Style for {diff.filename}", review_text=resp, approved=approved.result)


@injected
async def a_pre_commit_review__code_style(
        a_review_python_diff: Callable[[FileDiff], Awaitable[Review]],
        /,
        git_info: GitInfo,
):
    """
    Reviews staged git changes and provides code style feedback.

    Args:
        git_info: Injected GitInfo object containing repository information

    Returns:
        Review object with feedback and approval status
    """
    # Check if there are staged changes
    if not git_info.has_staged_changes:
        logger.info("No staged changes to review.")
        return Review(
            name="Code Style",
            review_text="No staged changes to review.",
            approved=True
        )

    # Check if there's diff content
    if not git_info.diff:
        logger.info("No diff content in staged changes.")
        return Review(
            name="Code Style",
            review_text="No diff content in staged changes.",
            approved=True
        )

    logger.info(f"Found {len(git_info.staged_files)} staged files. Reviewing diff...")
    if git_info.has_python_changes:
        python_diffs = git_info.python_diffs
        # Always show the progress bar, it's helpful feedback
        bar = tqdm(desc="Reviewing Python changes", total=len(python_diffs))

        async def task(diff):
            res = await a_review_python_diff(diff)
            bar.update(1)
            return res

        tasks = [task(diff) for diff in python_diffs.values()]
        reviews = await asyncio.gather(*tasks)
        bar.close()
        approved = all(r.approved for r in reviews)
        rejected_reviews = [r for r in reviews if not r.approved]
        if not approved:
            logger.warning("Code style violations found in Python changes.")
            review_text = ""
            for r in rejected_reviews:
                review_text += f"{r.name}:\n{r.review_text}\n"
        else:
            review_text = "No code style violations found in Python changes."
        return Review(name="Pinjected Coding Style", review_text=review_text, approved=approved)
    else:
        logger.info("No Python changes found in staged files.")
        return Review(
            name="Pinjected Coding Style",
            review_text="No Python changes found in staged files.",
            approved=True
        )
