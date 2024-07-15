import inspect
from dataclasses import dataclass
from typing import Callable, Any

ArgsModifier = Callable[[tuple, dict], tuple[tuple, dict, list["Injected"]]]


@dataclass
class KeepArgsPure:  # ArgsModifier
    signature: inspect.Signature
    targets: set[str]  # arguments in this targets will be wrapped with Injected.Pure()

    def __call__(self, args: Any, kwargs: Any) -> tuple[tuple, dict]:
        from pinjected import Injected
        # from loguru import logger
        # logger.info(f"args:{args},kwargs:{kwargs}")
        # logger.info(f"signature:{self.signature}")

        bound = self.signature.bind(*args, **kwargs)
        bound.apply_defaults()

        new_args = []
        new_kwargs = {}
        results = []

        for name, value in bound.arguments.items():
            param = self.signature.parameters[name]

            if param.kind == param.VAR_POSITIONAL:
                new_args.extend(Injected.pure(arg) if name in self.targets else arg for arg in value)
            elif param.kind == param.VAR_KEYWORD:
                new_kwargs.update({k: Injected.pure(v) if name in self.targets else v for k, v in value.items()})
            else:
                if name in self.targets:
                    results.append(value)
                wrapped_value = Injected.pure(value) if name in self.targets else value
                if param.kind in (param.POSITIONAL_ONLY,param.POSITIONAL_OR_KEYWORD):
                    new_args.append(wrapped_value)
                elif param.kind == param.KEYWORD_ONLY:
                    new_kwargs[name] = wrapped_value

        return tuple(new_args), new_kwargs, results
