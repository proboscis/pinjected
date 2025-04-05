from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Protocol

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
        return {k: v for k, v in self.file_diffs.items() if k.name.endswith('.py') and v.diff}


@dataclass
class Review:
    name: str
    review_text: str
    approved: bool


class Approved(BaseModel):
    result: bool

class PreCommitReviewer(Protocol):
    async def __call__(self, git_info: GitInfo) -> Review:
        """
        Run the reviewer on the provided git information.
        """
        pass