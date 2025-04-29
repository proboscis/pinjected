from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel


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
    def __repr__(self):
        return f"FileDiff(filename={self.filename}, diff_length={len(self.diff)}, is_binary={self.is_binary}, is_new_file={self.is_new_file}, is_deleted={self.is_deleted})"


@dataclass
class GitInfo:
    """
    Structured representation of git repository information.
    """
    # Current state
    branch: str
    staged_files: list[Path]
    modified_files: list[Path]
    untracked_files: list[Path]

    # Diff content
    diff: str

    # Per-file diffs for staged files
    file_diffs: dict[Path, FileDiff] = field(default_factory=dict)

    # Repository info
    repo_root: Path | None = None
    author_name: str | None = None
    author_email: str | None = None

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
    def python_diffs(self) -> dict[Path, FileDiff]:
        return {k: v for k, v in self.file_diffs.items() if k.name.endswith('.py') and v.diff}


@dataclass
class Review:
    name: str
    review_text: str
    approved: bool

    def __repr__(self):
        return f"Review(name={self.name}, approved={self.approved}, len_review_text={len(self.review_text)})"


class Approved(BaseModel):
    result: bool

class PreCommitReviewer(Protocol):
    async def __call__(self, git_info: GitInfo) -> Review:
        """
        Run the reviewer on the provided git information.
        """
