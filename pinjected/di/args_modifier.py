import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pinjected import Injected

ArgsModifier = Callable[[tuple, dict], tuple[tuple, dict, list["Injected"]]]


def _enhance_type_error(
    error: TypeError,
    function_name: str | None,
    source_file: str | None,
    line_number: int | None,
    signature: inspect.Signature,
    args: tuple,
) -> str:
    """Enhance TypeError message with function name and location information."""
    error_msg = str(error)

    if function_name:
        # Add function name to the error message
        if (
            error_msg.startswith("missing a required argument:")
            or error_msg.startswith("got an unexpected keyword argument")
            or "keyword-only" in error_msg
        ):
            error_msg = f"{function_name}() {error_msg}"
        elif error_msg.startswith("too many positional arguments"):
            # Create more specific error message for too many positional args
            positional_params = [
                p
                for p in signature.parameters.values()
                if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            ]
            error_msg = f"{function_name}() takes {len(positional_params)} positional argument(s) but {len(args)} were given"
        else:
            # For any other TypeError, prepend the function name
            error_msg = f"{function_name}() {error_msg}"

    # Add file location if available
    if source_file and line_number:
        error_msg += f"\n  File: {source_file}:{line_number}"
    elif source_file:
        error_msg += f"\n  File: {source_file}"

    return error_msg


def _wrap_if_target(value: Any, name: str, targets: set[str]) -> Any:
    """Wrap value with Injected.pure() if parameter name is in targets."""
    from pinjected import Injected

    return Injected.pure(value) if name in targets else value


def _process_var_positional(value: tuple, name: str, targets: set[str]) -> list:
    """Process VAR_POSITIONAL parameters."""
    return [_wrap_if_target(arg, name, targets) for arg in value]


def _process_var_keyword(value: dict, name: str, targets: set[str]) -> dict:
    """Process VAR_KEYWORD parameters."""
    return {k: _wrap_if_target(v, name, targets) for k, v in value.items()}


def _process_regular_param(
    name: str,
    value: Any,
    param: inspect.Parameter,
    targets: set[str],
    new_args: list,
    new_kwargs: dict,
    results: list,
) -> None:
    """Process regular (non-VAR) parameters."""
    if name in targets:
        results.append(value)

    wrapped_value = _wrap_if_target(value, name, targets)

    if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
        new_args.append(wrapped_value)
    elif param.kind == param.KEYWORD_ONLY:
        new_kwargs[name] = wrapped_value


@dataclass
class KeepArgsPure:  # ArgsModifier
    signature: inspect.Signature
    targets: set[str]  # arguments in this targets will be wrapped with Injected.Pure()
    function_name: str | None = None  # Optional function name for better error messages
    source_file: str | None = None  # Source file where the function is defined
    line_number: int | None = None  # Line number where the function is defined

    def __call__(self, args: Any, kwargs: Any) -> tuple[tuple, dict]:
        # Bind arguments to signature
        try:
            bound = self.signature.bind(*args, **kwargs)
        except TypeError as e:
            error_msg = _enhance_type_error(
                e,
                self.function_name,
                self.source_file,
                self.line_number,
                self.signature,
                args,
            )
            raise TypeError(error_msg) from None

        bound.apply_defaults()

        # Process bound arguments
        new_args = []
        new_kwargs = {}
        results = []

        for name, value in bound.arguments.items():
            param = self.signature.parameters[name]

            if param.kind == param.VAR_POSITIONAL:
                new_args.extend(_process_var_positional(value, name, self.targets))
            elif param.kind == param.VAR_KEYWORD:
                new_kwargs.update(_process_var_keyword(value, name, self.targets))
            else:
                _process_regular_param(
                    name, value, param, self.targets, new_args, new_kwargs, results
                )

        return tuple(new_args), new_kwargs, results
