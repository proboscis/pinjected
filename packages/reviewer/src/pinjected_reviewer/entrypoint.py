import asyncio
import importlib.resources
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Awaitable, List, Optional, Tuple, Dict

from loguru import logger
from pinjected import *
from pinjected_openai.openrouter.instances import StructuredLLM
from pydantic import BaseModel
from tqdm import tqdm

from pinjected_reviewer.utils import check_if_file_should_be_ignored

# a_openrouter_chat_completion()

GatherGitDiff = Callable[[], Awaitable[str]]


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


@dataclass
class FileDiff:
    """
    Information about a specific file diff in the git repository.
    """
    filename: Path
    diff: str
    is_binary: bool = False
    is_new_file: bool = False
    is_deleted: bool = False


@dataclass
class GitInfo:
    """
    Structured representation of git repository information.
    """
    # Current state
    branch: str
    staged_files: List[Path]
    modified_files: List[Path]
    untracked_files: List[Path]

    # Diff content
    diff: str

    # Per-file diffs for staged files
    file_diffs: Dict[Path, FileDiff] = field(default_factory=dict)

    # Repository info
    repo_root: Optional[Path] = None
    author_name: Optional[str] = None
    author_email: Optional[str] = None

    @property
    def has_staged_changes(self) -> bool:
        return len(self.staged_files) > 0

    @property
    def has_unstaged_changes(self) -> bool:
        return len(self.modified_files) > 0

    @property
    def has_untracked_files(self) -> bool:
        return len(self.untracked_files) > 0

    @property
    def has_python_changes(self) -> bool:
        return any(f.name.endswith('.py') for f in self.staged_files + self.modified_files)

    @property
    def python_diffs(self) -> Dict[Path, FileDiff]:
        return {k: v for k, v in self.file_diffs.items() if k.name.endswith('.py')}


@dataclass
class Review:
    name: str
    review_text: str
    approved: bool


class Approved(BaseModel):
    result: bool


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


@instance
async def review_diff__pinjected_code_style(
        a_review_python_diff: Callable[[FileDiff], Awaitable[Review]],
        git_info: GitInfo
) -> Review:
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


@injected
async def a_system(command: str, *args) -> Tuple[str, str]:
    """
    Generic function to execute system commands asynchronously.
    
    Args:
        command: The command to execute
        *args: Additional arguments for the command
    
    Returns:
        A tuple of (stdout, stderr) as strings
        
    Raises:
        RuntimeError: If the command fails (non-zero return code)
        Exception: Any other exceptions that occur during execution
    """
    cmd = [command]
    if args:
        cmd.extend(args)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    stderr_str = stderr.decode().strip()
    stdout_str = stdout.decode().strip()

    if process.returncode != 0:
        error_msg = f"Command {command} failed with code {process.returncode}: {stderr_str}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    return stdout_str, stderr_str


@instance
async def git_info(a_system) -> GitInfo:
    """
    Provides a GitInfo instance with comprehensive git repository information.
    Using @instance because it returns a value (not a function).
    
    Args:
        a_system: System command execution function
    
    Returns:
        A GitInfo object with repository details, file status, and diff content.
        
    Raises:
        RuntimeError: If a critical git command fails
    """
    # Get repository info
    try:
        stdout, _ = await a_system("git", "rev-parse", "--show-toplevel")
        repo_root = Path(stdout)
    except RuntimeError as e:
        logger.warning(f"Failed to get repository root: {e}")
        # This is critical - we need to know we're in a git repo
        raise RuntimeError("Not in a git repository or git not installed") from e

    # Get current branch
    try:
        stdout, _ = await a_system("git", "rev-parse", "--abbrev-ref", "HEAD")
        branch = stdout
    except RuntimeError as e:
        logger.warning(f"Failed to get current branch: {e}")
        branch = "unknown"

    # Get author info - not critical, can proceed without it
    try:
        stdout, _ = await a_system("git", "config", "user.name")
        author_name = stdout
    except RuntimeError:
        logger.info("Failed to get git user name")
        author_name = None

    try:
        stdout, _ = await a_system("git", "config", "user.email")
        author_email = stdout
    except RuntimeError:
        logger.info("Failed to get git user email")
        author_email = None

    # Get staged files - critical for our purpose
    try:
        stdout, _ = await a_system("git", "diff", "--name-only", "--staged")
        staged_files = [Path(f) for f in stdout.split('\n') if f] if stdout else []
    except RuntimeError as e:
        logger.error(f"Failed to get staged files: {e}")
        raise RuntimeError("Cannot get staged files information") from e

    # Get modified but unstaged files
    try:
        stdout, _ = await a_system("git", "diff", "--name-only")
        modified_files = [Path(f) for f in stdout.split('\n') if f] if stdout else []
    except RuntimeError as e:
        logger.warning(f"Failed to get modified files: {e}")
        modified_files = []

    # Get untracked files
    try:
        stdout, _ = await a_system("git", "ls-files", "--others", "--exclude-standard")
        untracked_files = [Path(f) for f in stdout.split('\n') if f] if stdout else []
    except RuntimeError as e:
        logger.warning(f"Failed to get untracked files: {e}")
        untracked_files = []

    # Get diff content - critical for our purpose
    try:
        stdout, _ = await a_system("git", "diff", "--staged")
        diff = stdout
    except RuntimeError as e:
        logger.error(f"Failed to get diff content: {e}")
        raise RuntimeError("Cannot get diff content") from e

    # Create file_diffs dictionary with per-file diffs
    file_diffs = {}
    for file_path in staged_files:
        try:
            # Check file type
            file_type_output, _ = await a_system("git", "diff", "--staged", "--name-status", "--", str(file_path))
            if file_type_output:
                file_type = file_type_output.split()[0]
                is_new_file = file_type == 'A'
                is_deleted = file_type == 'D'
            else:
                is_new_file = False
                is_deleted = False

            # Get file diff
            file_diff, _ = await a_system("git", "diff", "--staged", "--", str(file_path))

            # Check if it's a binary file
            is_binary = "Binary files" in file_diff

            file_diffs[file_path] = FileDiff(
                filename=file_path,
                diff=file_diff,
                is_binary=is_binary,
                is_new_file=is_new_file,
                is_deleted=is_deleted
            )
        except Exception as e:
            logger.warning(f"Failed to get diff for {file_path}: {e}")
            # Add an empty diff entry
            file_diffs[file_path] = FileDiff(
                filename=file_path,
                diff=f"[Error: {str(e)}]",
                is_binary=False
            )

    return GitInfo(
        branch=branch,
        staged_files=staged_files,
        modified_files=modified_files,
        untracked_files=untracked_files,
        diff=diff,
        file_diffs=file_diffs,
        repo_root=repo_root,
        author_name=author_name,
        author_email=author_email
    )


test_git_info: IProxy = git_info
check_git_info_py: IProxy = git_info.python_diffs
test_review: IProxy = review_diff__pinjected_code_style


@injected
async def a_git_diff(a_system, /) -> str:
    """
    Gathers the current git diff for staged files.
    
    Args:
        a_system: System command execution function
    
    Returns:
        A string containing the git diff output for staged changes.
        
    Raises:
        RuntimeError: If the git command fails
    """
    stdout, _ = await a_system("git", "diff", "--staged")

    # If no staged changes, return empty string
    if not stdout.strip():
        return ""

    return stdout


__meta_design__ = design(
    overrides=design(

    )
)
