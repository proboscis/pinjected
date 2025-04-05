import asyncio
import pwd
import subprocess
from pathlib import Path
from typing import Tuple

from loguru import logger

from pinjected import injected, instance, IProxy
from pinjected_reviewer.schema.types import GitInfo, FileDiff


@injected
async def a_system(logger, /, command: str, *args) -> Tuple[str, str]:
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
    logger.debug(f"running command: {command} {' '.join(args)}")
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


@injected
async def a_file_diff(logger,a_system, /, file_path: Path) -> str:
    pwd = Path.cwd()
    logger.info(f"current working directory: {pwd}")
    file_diff, stderr = await a_system("git", "--no-pager", "diff", "--color=never", "--staged", "--", str(file_path))
    return file_diff


run_test_diff: IProxy = a_file_diff(Path("../../pinjected/examples/demo_service.py"))


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
        staged_files = [Path(repo_root) / f for f in stdout.split('\n') if f] if stdout else []
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
