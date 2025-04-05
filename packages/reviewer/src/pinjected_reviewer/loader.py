from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Callable, Union, Awaitable, TypeVar

from pydantic import BaseModel
from returns.future import future_safe, Future, future
from returns.io import IOResultE
from returns.maybe import Maybe, Nothing, Some
from returns.pipeline import is_successful
from returns.unsafe import unsafe_perform_io

from pinjected import instance, injected
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
async def all_reviewers_from__from_markdowns(
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


def log_failure_as_table(items: list[IOResultE]):
    failures = [r for r in items if not is_successful(r)]
    succeeded = [r for r in items if is_successful(r)]

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title=f"Results: {len(succeeded)} succeeded, {len(failures)} failed")
    table.add_column("Status", style="green")
    table.add_column("Error", style="red")

    for failure in failures:
        error_message = str(failure.failure())
        table.add_row("Failed", error_message)

    console.print(table)


@instance
async def all_reviewers(
        all_reviewers_from__from_markdowns: list[IOResultE[Reviewer]],
) -> list[Reviewer]:
    log_failure_as_table(all_reviewers_from__from_markdowns)
    succeeded = [r for r in all_reviewers_from__from_markdowns if is_successful(r)]
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
Please provide a detailed review and indicate if the changes are approved or not.
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
async def file_diff_reviewers(logger,all_reviewers: list[Reviewer]) -> list[Reviewer[FileDiff]]:
    res = []
    for r in all_reviewers:
        logger.info(f"Reviewer: {r.name}, Interests: {r.interests}")
        match list(r.interests):
            case [PreCommitFileDiffInterest(), *_]:
                res.append(r)
            case _:
                pass

    return res


@instance
async def pre_commit_reviews__phased(
        a_map_progress,
        git_info,
        git_info_reviewers: list[Reviewer[GitInfo]],
        file_diff_reviewers: list[Reviewer[FileDiff]],
):
    """
    1. gather all Reviewer instances
    2. proceed with stages
    3. query reviewers per stage
    """
    # 1. first stage, reviews that want GitInfo
    # how do i get reviewers that want gitinfo?
    reviews = []

    async def git_info_review(reviewer: Reviewer[GitInfo]):
        return ReviewResult(git_info, await reviewer(git_info))

    async for reviewer in a_map_progress(
            git_info_review,
            git_info_reviewers,
            desc="Running GitInfo reviewers",
    ):
        reviews.append(reviewer)

    # 2. second stage, reviews that want file diffs

    async def file_review(reviewer) -> list[FileDiff]:
        async def task(diff: FileDiff):
            return ReviewResult(diff, await reviewer(diff))

        results = []
        async for item in a_map_progress(
                task,
                git_info.file_diffs.values(),
                desc=f"Running {reviewer.name}...",
        ):
            results.append(item)

        return results

    async for reviewer in a_map_progress(
            file_review,
            file_diff_reviewers,
            desc="Running FileDiff reviewers",
    ):
        reviews.extend(reviewer)
    return reviews
