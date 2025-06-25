from typing import TYPE_CHECKING, Protocol

from pinjected.v2.keys import StrBindKey

if TYPE_CHECKING:
    from pinjected.run_helpers.run_injected import RunContext


class PinjectedHandleMainException(Protocol):
    """
    Caleld when an exception is raised in the pinjected runner (run_anything)
    """

    key = StrBindKey("__pinjected_handle_main_exception__")

    async def __call__(self, context: "RunContext", e: Exception) -> str | None:
        """
        param context: the run context containing design, overrides, and variable information
        param e: the exception that was raised
        return: if None, the exception will be raised again.
        """


class PinjectedHandleMainResult(Protocol):
    """
    Called when the run was successful in the pinjected runner (run_anything)
    """

    key = StrBindKey("__pinjected_handle_main_result__")

    async def __call__(self, context: "RunContext", result):
        """
        param context: the run context containing design, overrides, and variable information
        param result: the result of the successful run
        """
        pass
