from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar, Union

from pydantic import BaseModel, Field
from returns.future import Future
from returns.maybe import Maybe

from pinjected_reviewer.schema.types import FileDiff, Review


class ReviewerAttributes_v4(BaseModel):
    """Represents attributes extracted from a reviewer markdown file."""

    name: str = Field(..., description="The name of the reviewer")
    when_to_trigger: Literal["pre_commit"] = Field(
        ..., description="When this reviewer should be triggered (e.g., pre_commit)"
    )
    review_type: Literal["approval"] = Field(
        ...,
        description="The return type of this reviewer, 'approval' means reviewer must answer with approved or rejected",
    )
    target_file_extension: str = Field(
        ...,
        description="The target file extension for this reviewer, e.g., '.py' for Python files. use * for all files",
    )
    review_scope: Literal["file_diff", "file_full"] = Field(
        ...,
        description="""
    The scope of the review. 'file_diff' means only the diff of the file is reviewed, 'file_full' means the entire file is reviewed.
    Default to 'file_diff'.
    """,
    )
    llm_name: str = Field(
        ...,
        description="""
    The name of the LLM to use for this reviewer. Must be compatible with openrouter model definition.
    Typical values:
    - google/gemini-2.0-flash-001
    - anthropic/claude-3.5-sonnet
    - anthropic/claude-3.7-sonnet:thinking
    - openai/gpt-4o
    - openai/gpt-4o-mini
    - deepseek/deepseek-chat
    """,
    )


ReviewerAttributes = ReviewerAttributes_v4


@dataclass
class MarkdownReviewerDefinition:
    attributes: ReviewerAttributes
    review_material: str
    material_path: Path | None = None


@dataclass(frozen=True)
class PreCommitGitInfoInterest:
    pass


@dataclass(frozen=True)
class PreCommitFileDiffInterest:
    file_extension: str | None = None


Interest = Union[PreCommitFileDiffInterest, PreCommitGitInfoInterest]
Interests = set[Interest]

# so, each reviewer can declare their interests and we should pick them up.
ReviewTarget = TypeVar("ReviewTarget")

ReviewerFunc = Callable[[ReviewTarget], Future[Review]]


class Reviewer(Protocol[ReviewTarget]):
    name: str
    interests: Interests

    async def __call__(self, target: ReviewTarget) -> Review:
        """
        Run the reviewer on the provided target.
        """


@dataclass
class ReviewResult:
    input: Any
    result: Review

    def __repr__(self):
        return f"ReviewResult(input={type(self.input)},name={self.result.name} approved={self.result.approved})"


SkipReasonProvider = Callable[[FileDiff], Future[Maybe[str]]]
