from typing import Callable, Awaitable

from pinjected import *

from pinjected_reviewer.reviewer_v1 import a_pre_commit_review__code_style
from pinjected_reviewer.schema.types import GitInfo, Review, PreCommitReviewer

# a_openrouter_chat_completion()

GatherGitDiff = Callable[[], Awaitable[str]]


@instance
async def pre_commit_reviews(
        git_info: GitInfo,
        pre_commit_reviewers: list[PreCommitReviewer],
        a_map_progress
) -> list[Review]:
    """
    Entrypoint to provide reviews on pre-commit hook.
    """

    async def task(reviewer: PreCommitReviewer):
        return await reviewer(git_info)

    res = []
    async for review in a_map_progress(
            task,
            pre_commit_reviewers,
            desc="Running pre-commit reviewers",
    ):
        res.append(review)

    return res


__meta_design__ = design(
    overrides=design(

    )
)
