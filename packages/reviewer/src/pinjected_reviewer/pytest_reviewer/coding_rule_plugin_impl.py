import asyncio
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal, Optional, Protocol

import pandas as pd
import pytest
from pinjected import *
from pinjected_openai.openrouter.instances import StructuredLLM
from tqdm import tqdm
from loguru import logger

from pinjected_reviewer.pytest_reviewer.inspect_code import DetectMisuseOfPinjectedProxies
from pinjected_reviewer.utils import check_if_file_should_be_ignored


@dataclass
class Diagnostic:
    name: str
    level: Literal['error', 'warning', 'suggest', 'approve']
    message: str
    file: Path
    line: Optional[int] = None
    column: Optional[int] = None


@instance
async def python_files_in_project(logger, pytest_session: pytest.Session) -> list[Path]:
    root = Path(pytest_session.config.rootpath)
    logger.info(f"pinjected_reviewer: rootpath: {root}")

    # Find all Python files in the project directory
    all_py_files = list(root.glob('**/*.py'))

    # Filter out files from Python libraries and virtual environments
    project_files = []
    for file_path in all_py_files:
        parts = file_path.parts
        # Skip files in virtual environments or site-packages
        if any(part in ['venv', '.venv', 'site-packages', '.tox', 'dist', 'build', '__pycache__'] for part in parts):
            continue
        project_files.append(file_path)

    logger.info(f"pinjected_reviewer: found {len(project_files)} Python files in project")
    return project_files


@instance
async def changed_python_files_in_project(
        logger,
        pytest_session: pytest.Session,
        git_info,
) -> list[Path]:
    """
    Gets only the changed Python files in the git repository (staged, unstaged, and untracked).
    Uses the existing git_info instance for git operations.
    
    Args:
        logger: Injected logger
        pytest_session: Current pytest session
        git_info: GitInfo instance with repository information
        
    Returns:
        A list of changed Python file paths (excluding deleted files)
    """
    root = Path(pytest_session.config.rootpath)
    logger.info(f"pinjected_reviewer: rootpath for changed files: {root}")

    # Get all Python files that have changes using git_info
    all_changed_files = []

    # Add staged Python files (filter out deleted files)
    staged_py_files = []
    for f in git_info.staged_files:
        if f.name.endswith('.py'):
            # Check if file is deleted
            is_deleted = False
            if f in git_info.file_diffs:
                is_deleted = git_info.file_diffs[f].is_deleted

            if not is_deleted:
                staged_py_files.append(f)

    all_changed_files.extend(staged_py_files)

    # Add modified (unstaged) Python files
    all_changed_files.extend([f for f in git_info.modified_files if f.name.endswith('.py')])

    # Add untracked Python files
    all_changed_files.extend([f for f in git_info.untracked_files if f.name.endswith('.py')])

    # Remove duplicates
    all_changed_files = list(set(all_changed_files))

    # Convert to absolute paths if needed
    project_files = [root / file_path if not file_path.is_absolute() else file_path for file_path in all_changed_files]

    # Filter out files from Python libraries and virtual environments
    # Also filter out files that don't exist (e.g., deleted files)
    filtered_files = []
    for file_path in project_files:
        parts = file_path.parts
        # Skip files in virtual environments or site-packages
        if any(part in ['venv', '.venv', 'site-packages', '.tox', 'dist', 'build', '__pycache__'] for part in parts):
            continue

        # Skip files that don't exist on disk
        if not file_path.exists():
            logger.warning(f"pinjected_reviewer: skipping non-existent file {file_path}")
            continue

        filtered_files.append(file_path)

    logger.info(f"pinjected_reviewer: found {len(filtered_files)} changed Python files")
    return filtered_files

class FileDiagnosisProvider(Protocol):
    async def __call__(self, src_path: Path) -> list[Diagnostic]:
        ...


@injected
async def a_map_progress(async_f, items, total: int = None, desc: str = None, n_concurrent: int = None):
    if n_concurrent is None:
        n_concurrent = 10
    sem = asyncio.Semaphore(n_concurrent)
    bar = tqdm(total=total, desc=desc)

    async def task(item):
        async with sem:
            res = await async_f(item)
        bar.update()
        return res

    res = await asyncio.gather(*[task(item) for item in items])
    bar.close()
    return res


class PinjectedReviewFailed(Exception):
    pass


@injected
async def a_pytest_plugin_impl(
        a_map_progress,
        python_files_in_project: list[Path],
        a_detect_injected_function_call_without_requesting: FileDiagnosisProvider,
        /,
):
    # remove __main__.py from the list
    python_files_in_project = [f for f in python_files_in_project if not f.name == '__main__.py']

    async def task(item):
        try:
            return await a_detect_injected_function_call_without_requesting(item)
        except Exception as e:
            raise PinjectedReviewFailed(f'Faield to diagnose {item}') from e

    diagnosis: list[list[Diagnostic]] = await a_map_progress(
        task,
        python_files_in_project,
        total=len(python_files_in_project),
        desc="Detecting misuse of pinjected proxies",
    )
    diagnosis: list[Diagnostic] = [d for ds in diagnosis for d in ds]
    return diagnosis


@injected
async def a_detect_injected_function_call_without_requesting(
        a_detect_misuse_of_pinjected_proxies: DetectMisuseOfPinjectedProxies,
        pinjected_guide_md: str,
        a_sllm_for_code_review: StructuredLLM,
        logger,
        /,
        src_path: Path
) -> list[Diagnostic]:
    """
    detect wrong usage of @injected function such as:
    @injected
    def service_function():pass
    @injected
    def user_function(arg):pass
        return service_function() # wrong! returns IProxy object
    # Correct usage:
    @injected
    def user_function(service_function,/,arg): # need to request the injected function
        return service_function(arg) # correct! returns the computed result

    # Warning case:
    def user_function()->int: # wrong! returns IProxy object. Perhaps the user doesnt know what he/she is doing.
        # we need to warn the user to either decorate and request the dependency as in the example above,
        # or instruct to annotate with IProxy[T] to indicate that the user is aware of the usage.
        return service_function()

    # correct case:
    def user_function()->IProxy[int]:# correct! the user knows what he/she is doing well. that he is correctly using IProxy object for purpose.
        return service_function()

    To implement this, we need to first find all function definitions in the files.
    find all symbols that are being called.
    check if the symbols are in the function arguments.
    if not in the function arguments, look for the definitions
    if it is annotated with @injected, then it is a wrong usage.
    """
    # Check if file should be ignored
    content = src_path.read_text()
    should_ignore = check_if_file_should_be_ignored(content, src_path)
    if should_ignore:
        return []

    misuses = await a_detect_misuse_of_pinjected_proxies(src_path)
    results = []
    guide = pinjected_guide_md
    # now we need to build a context to ask llm for fix:
    # lets filter misuses with same file and numbers
    df = pd.DataFrame([{**asdict(m), **dict(start=m.src_node.lineno, end=m.src_node.end_lineno)} for m in misuses])
    if df.empty:
        return []
    df = df.groupby(['user_function', 'line_number']).first()
    context = ""
    whole_src = src_path.read_text().splitlines()
    # add line no
    whole_src = [f"{i + 1:4d}: {line}" for i, line in enumerate(whole_src)]
    for user_function, group in df.groupby('user_function'):
        start = group.iloc[0].start
        end = group.iloc[0].end
        func_src = "\n".join(whole_src[start - 3:end])
        context += f"""
# We found possible misuse of pinjected proxy objects in the function `{user_function}`.
line {start} to {end}:
Source:
{func_src}
"""
        for i, m in group.reset_index().iterrows():
            context += f"""
## Mistake in line {m.line_number}: {m.misuse_type}, {m.used_proxy.split('.')[-1]}
"""
    logger.debug(f"context: {context}")

    prompt = f"""
Read the following guide for how to use pinjected.
{guide}

Now, we found following possible misuses of pinjected proxies in the code:
{context}

Please provide a detailed guide to explain how the code should be fixed, for each mistake.
Please only provide the correct use of @injected and @instance, rather than hacking anyway to make the code work.
IProxy objects can be used to construct a tree of IProxy, but the user should be aware of the usage.
"""
    resp: str = await a_sllm_for_code_review(prompt)
    return [Diagnostic(
        name='Misuse of pinjected proxies',
        level='warning',
        message=resp,
        file=src_path
    )]


import pinjected_reviewer

test_a_detect_injected_function_call_without_requesting: IProxy = a_detect_injected_function_call_without_requesting(
    Path(pinjected_reviewer.pytest_reviewer.inspect_code.__file__)
)

with design(
        python_files_in_project=list(Path(__file__).parent.parent.glob('**/*.py')),
):
    test_a_pytest_plugin_impl: IProxy = a_pytest_plugin_impl()


@injected
async def a_review_python_pinjected(src_path: Path):
    pass


__meta_design__ = design()
