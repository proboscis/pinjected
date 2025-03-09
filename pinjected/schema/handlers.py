from typing import Protocol, Optional

from pinjected.v2.keys import StrBindKey


class PinjectedHandleMainException(Protocol):
    """
    Caleld when an exception is raised in the pinjected runner (run_anything)
    """
    key = StrBindKey('__pinjected_handle_main_exception__')

    async def __call__(self, e: Exception) -> Optional[str]:
        """
        param e: the exception that was raised
        return: if None, the exception will be raised again.
        """


class PinjectedHandleMainResult(Protocol):
    """
    Called when the run was successful in the pinjected runner (run_anything)
    """
    key = StrBindKey('__pinjected_handle_main_result__')

    async def __call__(self, result): pass
