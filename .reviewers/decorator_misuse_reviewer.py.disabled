from dataclasses import dataclass, field
from typing import Callable

from pinjected import injected, IProxy
from pinjected_reviewer.pytest_reviewer.coding_rule_plugin_impl import Diagnostic
from pinjected_reviewer.schema.reviewer_def import Reviewer, PreCommitFileDiffInterest
from pinjected_reviewer.schema.types import FileDiff, Review


@dataclass
class DecoratorMisuseDetector(Reviewer[FileDiff]):
    _a_detect_injected_function_call_without_requesting: Callable
    name: str = "Pinjected Decorator Misuse Reviewer"
    interests: set = field(default_factory=lambda: {PreCommitFileDiffInterest(".py")})

    async def __call__(self, file_diff: FileDiff) -> Review:
        if not str(file_diff.filename).endswith(".py"):
            return Review(
                name="Pinjected Decorator Misuse Reviewer",
                review_text="skipped since non-python file",
                approved=True
            )
        diagnostics: list[Diagnostic] = await self._a_detect_injected_function_call_without_requesting(
            file_diff.filename
        )
        if not diagnostics:
            return Review(
                name="Pinjected Decorator Misuse Reviewer",
                review_text="No pinjected decorator misuse detected.",
                approved=True
            )
        return Review(
            name="Pinjected Decorator Misuse Reviewer",
            review_text="\n".join([d.message for d in diagnostics]),
            approved=False
        )

    def __repr__(self):
        return f"DecoratorMisuseDetector(name={self.name}, interests={self.interests})"


# this is automatically picked up by pinjected-reviewer. must be a type of IProxy[Reviewer]
__reviewer__: IProxy[Reviewer] = injected(DecoratorMisuseDetector)()
