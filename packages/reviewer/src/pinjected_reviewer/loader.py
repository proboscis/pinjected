from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Callable, Union, Awaitable, TypeVar

from pydantic import BaseModel
from returns.future import future_safe, Future, future, FutureResultE
from returns.io import IOResultE
from returns.maybe import Maybe, Nothing, Some
from returns.pipeline import is_successful
from returns.unsafe import unsafe_perform_io

from pinjected import instance, injected, IProxy
from pinjected.run_config_utils import load_variable_from_script
from pinjected.v2.async_resolver import create_tb
from pinjected_openai.openrouter.instances import StructuredLLM
from pinjected_reviewer.reviewer_v1 import ExtractApproved
from pinjected_reviewer.schema.reviewer_def import ReviewerAttributes_v4, MarkdownReviewerDefinition, \
    PreCommitFileDiffInterest, Reviewer, ReviewResult, PreCommitGitInfoInterest, Interests, SkipReasonProvider
from pinjected_reviewer.schema.types import GitInfo, Review, FileDiff


@injected
async def a_llm_factory_for_reviewer(
        a_cached_openrouter_chat_completion,
        /,
        model_name
) -> StructuredLLM:
    async def impl(text: str, response_format: type[BaseModel] = None) -> Union[str, BaseModel]:
        return await a_cached_openrouter_chat_completion(
            prompt=text,
            model=model_name,
            response_format=response_format
        )

    return impl


@injected
async def a_reviewer_definition_from_path(
        a_structured_llm_for_markdown_extraction: StructuredLLM,
        logger,
        /,
        path: Path
) -> MarkdownReviewerDefinition:
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
        response_format=ReviewerAttributes_v4
    )
    return MarkdownReviewerDefinition(
        attributes=attributes,
        review_material=content,
        material_path=path,
    )


@injected
async def a_markdown_reviewer_def_to_reviewer(
        a_llm_factory_for_reviewer: Callable[[str], Awaitable[StructuredLLM]],
        a_extract_approved,
        /,
        rev_def: MarkdownReviewerDefinition,
) -> Reviewer:
    """
    Convert a MarkdownReviewerDefinition to a Reviewer instance.

    Args:
        rev_def: The markdown reviewer definition

    Returns:
        A Reviewer instance
    """

    no_skip = lambda _: Future.from_value(Nothing)

    def get_skipper(ext) -> SkipReasonProvider:
        if ext == '*':
            return no_skip

        @future
        async def reason_to_skip(file_diff: FileDiff) -> Maybe[str]:
            _ext = ext.replace('*', '')
            if not file_diff.filename.name.endswith(_ext):
                return Some(f"Skipped review for {file_diff.filename.name} due to file extension {_ext}")
            return Nothing

        return reason_to_skip

    match (rev_def.attributes.when_to_trigger, rev_def.attributes.review_scope):
        case ('pre_commit', 'file_diff'):
            return MarkdownFileDiffReviewer(
                llm=await a_llm_factory_for_reviewer(rev_def.attributes.llm_name),
                a_extract_approved=a_extract_approved,
                name=rev_def.attributes.name,
                material=rev_def.review_material,
                reason_to_skip=get_skipper(rev_def.attributes.target_file_extension),
                interests={PreCommitFileDiffInterest(rev_def.attributes.target_file_extension)},
            )

    raise ValueError(
        f"Unsupported reviewer definition: {rev_def} "
    )


@injected
def reviewer_paths(logger, /, repo_root: Path) -> List[Path]:
    """
    Return a list of paths to load reviewer files from.
    
    Args:
        logger: Logger instance
        repo_root: The root directory of the repository
        
    Returns:
        List of paths to search for reviewer files
    """
    home_reviewers = Path("~/.reviewers").expanduser()
    return [repo_root / ".reviewers", home_reviewers]


@injected
def find_reviewer_markdown_files(
        logger,
        reviewer_paths,
        /,
        repo_root: Path
) -> List[Path]:
    """
    Find all markdown files in the paths provided by reviewer_paths.
    
    Args:
        logger: Logger instance
        reviewer_paths: Function that returns paths to search for reviewer files
        repo_root: The root directory of the repository
        
    Returns:
        List of paths to reviewer markdown files
    """
    paths = reviewer_paths(repo_root)
    markdown_files = []
    
    for path in paths:
        if not path.exists():
            logger.warning(f"Reviewers directory not found: {path}")
            continue
            
        markdown_files.extend(list(path.glob("*.md")))
    
    logger.info(f"Found {len(markdown_files)} reviewer definition files in {paths}")
    return markdown_files


@instance
async def reviewer_definitions(
        repo_root: Path,
        a_reviewer_definition_from_path,
        find_reviewer_markdown_files,
        a_map_progress,
) -> List[IOResultE[MarkdownReviewerDefinition]]:
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
    safe_get_reviewer = future_safe(a_reviewer_definition_from_path)
    async for res in a_map_progress(safe_get_reviewer, markdown_files, desc="Loading reviewer definitions"):
        definitions.append(res)
    return definitions


X = TypeVar('X')
Y = TypeVar('Y')


def map_io_result(f: Callable[[X], Y], items: list[IOResultE]) -> list[IOResultE]:
    """
    Map a function over a list of IOResultE items.

    Args:
        f: Function to apply
        items: List of IOResultE items

    Returns:
        List of IOResultE items
    """
    return [item.map(f) for item in items]


@instance
async def all_reviewers__from_markdowns(
        repo_root,
        a_map_progress,
        a_reviewer_definition_from_path,
        find_reviewer_markdown_files,
        a_markdown_reviewer_def_to_reviewer: Callable[[MarkdownReviewerDefinition], Awaitable[Reviewer]],
) -> List[IOResultE[Reviewer]]:
    """
    Load all reviewers from markdown files.

    Args:
        a_map_progress: Function to map progress
        a_reviewer_definition_from_path: Function to create a ReviewerDefinition from a file path
        find_reviewer_markdown_files: Function to find reviewer markdown files

    Returns:
        List of ReviewerDefinition instances
    """
    markdown_files = find_reviewer_markdown_files(repo_root)
    reviewers: list[IOResultE[Reviewer]] = []

    @future_safe
    async def task(file_path: Path) -> Reviewer:
        r_def: MarkdownReviewerDefinition = await a_reviewer_definition_from_path(file_path)
        reviewer: Reviewer = await a_markdown_reviewer_def_to_reviewer(r_def)
        return reviewer

    async for res in a_map_progress(task, markdown_files, desc="Loading reviewer definitions"):
        reviewers.append(res)
    return reviewers


@injected
@future_safe
async def a_py_file_to_reviewer(__resolver__, /, path: Path) -> Reviewer:
    """
    Load a reviewer from a Python file.
    Expects the file to contain a variable named __reviewer__:IProxy[Reviewer].
    """
    reviewer_iproxy: IProxy[Reviewer] = load_variable_from_script(path, "__reviewer__")
    reviewer: Reviewer = await __resolver__[reviewer_iproxy]
    return reviewer


@instance
async def all_reviewers__from_python_files(
        a_py_file_to_reviewer,
        a_await_all,
        repo_root,
        reviewer_paths,
) -> list[IOResultE[Reviewer]]:
    """
    Load all reviewers from Python files in the paths provided by reviewer_paths.
    """
    paths = reviewer_paths(repo_root)
    py_files = []
    
    for path in paths:
        if path.exists():
            py_files.extend(list(path.glob("*.py")))
            
    reviewers: list[FutureResultE[Reviewer]] = [a_py_file_to_reviewer(py_file) for py_file in py_files]
    reviewers: list[IOResultE[Reviewer]] = await a_await_all(reviewers,
                                                           desc="Loading reviewer definitions from python files")
    return reviewers


def log_failure_as_table(items: list[IOResultE]):
    failures = [r for r in items if not is_successful(r)]
    succeeded = [r for r in items if is_successful(r)]

    from rich.console import Console
    from rich.table import Table

    if failures:
        console = Console()
        table = Table(title=f"Results: {len(succeeded)} succeeded, {len(failures)} failed")
        table.add_column("Status", style="green")
        table.add_column("Error", style="red")

        for failure in failures:
            error_message = str(failure.failure())
            table.add_row("Failed", error_message)
            print(create_tb(failure))
            print(failure)
        console.print(table)


@instance
async def all_reviewers(
        all_reviewers__from_markdowns: list[IOResultE[Reviewer]],
        all_reviewers__from_python_files: list[IOResultE[Reviewer]],
) -> list[Reviewer]:
    src_reviewers = all_reviewers__from_python_files + all_reviewers__from_markdowns
    log_failure_as_table(src_reviewers)
    succeeded = [r for r in src_reviewers if is_successful(r)]
    return [unsafe_perform_io(item.unwrap()) for item in succeeded]


@dataclass
class MarkdownFileDiffReviewer(Reviewer[FileDiff]):
    llm: StructuredLLM
    a_extract_approved: ExtractApproved
    name: str
    material: str
    reason_to_skip: SkipReasonProvider = field(default=lambda _: Future.from_value(Nothing))
    interests: Interests = field(default_factory=lambda: {PreCommitFileDiffInterest()})

    async def __call__(self, file_diff: FileDiff) -> Review:
        skip_reason: Maybe[str] = unsafe_perform_io(await self.reason_to_skip(file_diff))
        match skip_reason:
            case Some(reason):
                return Review(
                    name=self.name,
                    review_text=f"Skipped review: {reason}",
                    approved=True
                )
        prompt = f"""
Review the following file diff and provide feedback.
File Diff:
{file_diff.diff}
Review Material:
{self.material}
If the content is out of scope of the provided material, please approve.
If the decision is to approve the change, the answer must be just "Approved", try to refrain from providing long answers.
Otherwise, please provide a detailed review and explain why the change is not approved, and how it should be fixed.
"""
        review = await self.llm(prompt)
        approved = await self.a_extract_approved(review)

        return Review(
            name=self.name,
            review_text=review,
            approved=approved.result
        )

    def __repr__(self) -> str:
        return f"MarkdownFileDiffReviewer(name={self.name}, interests={self.interests} material_length={len(self.material)})"


@instance
async def git_info_reviewers(all_reviewers: list[Reviewer]) -> list[Reviewer[GitInfo]]:
    res = []
    for r in all_reviewers:
        match r.interests:
            case [PreCommitGitInfoInterest(), *_]:
                res.append(r)
            case _:
                pass
    return res


@instance
async def file_diff_reviewers(logger, all_reviewers: list[Reviewer]) -> list[Reviewer[FileDiff]]:
    res = []
    for r in all_reviewers:
        logger.info(f"Reviewer: {r.name}, Interests: {r.interests}")
        match list(r.interests):
            case [PreCommitFileDiffInterest(), *_]:
                res.append(r)
            case _:
                pass

    return res


@injected
async def a_await_all(a_map_progress, /, tasks: list[FutureResultE], desc: str = None) -> list[IOResultE]:
    """
    Await all tasks and return the results, using a_map_progress for progress tracking.
    Basically converting list of FutureResultE to list of IOResultE
    """
    result: list[IOResultE] = []

    async def awaiter(item: FutureResultE) -> IOResultE:
        return await item

    async for item in a_map_progress(
            awaiter,
            tasks,
            desc=desc,
            total=len(tasks),
    ):
        result.append(item)
    return result


@instance
async def pre_commit_reviews__phased(
        a_await_all,
        git_info,
        git_info_reviewers: list[Reviewer[GitInfo]],
        file_diff_reviewers: list[Reviewer[FileDiff]],
) -> list[ReviewResult]:
    @future_safe
    async def git_info_review(reviewer: Reviewer[GitInfo]):
        return ReviewResult(git_info, await reviewer(git_info))

    tasks: list[FutureResultE[ReviewResult]] = []
    tasks += [git_info_review(reviewer) for reviewer in git_info_reviewers]

    # 2. second stage, reviews that want file diffs
    @future_safe
    async def review_file(reviewer: Reviewer[FileDiff], diff: FileDiff):
        return ReviewResult(diff, await reviewer(diff))

    for reviewer in file_diff_reviewers:
        for file_diff in git_info.file_diffs.values():
            file_diff:FileDiff
            if file_diff.filename.exists():
                tasks.append(review_file(reviewer, file_diff))

    reviews: list[IOResultE[ReviewResult]] = await a_await_all(tasks, desc="Running reviewers")
    log_failure_as_table(reviews)
    succeeded = [unsafe_perform_io(r).unwrap() for r in reviews if is_successful(r)]
    return succeeded
