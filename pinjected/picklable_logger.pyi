"""Type stubs for picklable_logger module."""

from typing import (
    Any,
    Dict,
    Union,
    Optional,
    Callable,
    Tuple,
    TextIO,
    TYPE_CHECKING,
    Iterator,
)
from contextlib import contextmanager
from pathlib import Path

if TYPE_CHECKING:
    from logging import Handler

class PicklableLogger:
    """A picklable wrapper around loguru logger."""

    _extra: Dict[str, Any]
    _disabled_modules: set[str]
    _opt_defaults: Dict[str, Any]

    def __init__(self) -> None: ...
    def bind(self, **kwargs) -> PicklableLogger: ...
    @contextmanager
    def contextualize(self, **kwargs) -> Any: ...
    def opt(
        self,
        *,
        lazy: bool = False,
        colors: bool = False,
        raw: bool = False,
        capture: bool = True,
        depth: int = 0,
        exception: Optional[
            Union[bool, BaseException, Tuple[type, BaseException, Any]]
        ] = None,
        record: bool = False,
        **kwargs,
    ) -> PicklableLogger: ...

    # Logging methods
    def trace(self, message: str, *args, **kwargs) -> None: ...
    def debug(self, message: str, *args, **kwargs) -> None: ...
    def info(self, message: str, *args, **kwargs) -> None: ...
    def success(self, message: str, *args, **kwargs) -> None: ...
    def warning(self, message: str, *args, **kwargs) -> None: ...
    def error(self, message: str, *args, **kwargs) -> None: ...
    def critical(self, message: str, *args, **kwargs) -> None: ...
    def exception(self, message: str, *args, **kwargs) -> None: ...
    def log(self, level: Union[str, int], message: str, *args, **kwargs) -> None: ...

    # Handler management
    def add(
        self,
        sink: Union[TextIO, str, Path, Callable, Handler],
        *,
        level: Union[str, int] = "DEBUG",
        format: Optional[Union[str, Callable]] = None,
        filter: Optional[Union[str, Dict, Callable]] = None,
        colorize: Optional[bool] = None,
        serialize: bool = False,
        backtrace: bool = True,
        diagnose: bool = True,
        enqueue: bool = False,
        catch: bool = True,
        **kwargs,
    ) -> int: ...
    def remove(self, handler_id: Optional[int] = None) -> None: ...

    # Configuration methods
    def configure(
        self, *, handlers=None, levels=None, extra=None, patcher=None, activation=None
    ) -> None: ...
    def level(
        self,
        name: Union[str, int],
        no: Optional[int] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Any: ...
    def disable(self, name: Optional[str] = None) -> None: ...
    def enable(self, name: Optional[str] = None) -> None: ...

    # Utility methods
    def catch(
        self,
        exception: Union[type, Tuple[type, ...]] = Exception,
        *,
        level: Union[str, int] = "ERROR",
        reraise: bool = False,
        onerror: Optional[Callable] = None,
        exclude: Optional[Union[type, Tuple[type, ...]]] = None,
        default: Optional[Any] = None,
        message: str = ...,
    ) -> Callable: ...
    def patch(self, patcher: Callable[[Dict], None]) -> None: ...
    def complete(self) -> None: ...
    @staticmethod
    def parse(
        file: Union[str, Path, TextIO],
        pattern: str,
        *,
        cast: Optional[Dict[str, Callable]] = None,
        chunk: int = 2**16,
    ) -> Iterator[Dict[str, Any]]: ...

    # Pickling support
    def __getstate__(self) -> Dict[str, Any]: ...
    def __setstate__(self, state: Dict[str, Any]) -> None: ...
