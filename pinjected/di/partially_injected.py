import inspect
from dataclasses import dataclass
from typing import Callable, Set, Optional

from pinjected import Injected
from pinjected.di.args_modifier import ArgsModifier
from pinjected.di.proxiable import DelegatedVar


def get_final_args_kwargs(
        modified_sig,
        original_sig,
        __injected__: dict,
        *args,
        **kwargs):
    """
    the target cannot be VAR_POSITIONAL or VAR_KEYWORD, i.e. *args, **kwargs

    iterate through original signature, and replace the injected targets with the provided values.
    the injected values may be Postional only, Positional or Keyword, or Keyword only. so we need to split them.
    """
    # from loguru import logger
    bound_args = modified_sig.bind(*args, **kwargs)
    # logger.info(f"original args: {args} kwargs: {kwargs}")
    # logger.info(f"injection targets:{__injected__}")
    new_args = []
    new_kwargs = {}

    def add_by_type(param, value):
        if param.kind == inspect.Parameter.POSITIONAL_ONLY:
            # logger.info(f"add {param.name} as args")
            new_args.append(value)
        elif param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
            # logger.info(f"add {param.name} as args")
            new_args.append(value)
        elif param.kind == inspect.Parameter.KEYWORD_ONLY:
            # logger.info(f"add {param.name} as kwargs")
            new_kwargs[param.name] = value
        # logger.info(f"current new_args:{new_args}, {new_kwargs}")

    for param in original_sig.parameters.values():
        # logger.info(f"checking param:{param}")
        if param.name in __injected__:
            # logger.info(f"add {param.name} by injection")
            add_by_type(param, __injected__[param.name])
        elif param.name in bound_args.arguments:
            # logger.info(f"add {param.name} by bound_args")
            add_by_type(param, bound_args.arguments[param.name])
        elif param.default != inspect.Parameter.empty:
            # logger.info(f"add {param.name} from default")
            add_by_type(param, param.default)

    bound_vargs = [varg for varg in modified_sig.parameters.values() if
                   varg.kind == inspect.Parameter.VAR_POSITIONAL]
    bound_kwargs = [varg for varg in modified_sig.parameters.values() if
                    varg.kind == inspect.Parameter.VAR_KEYWORD]

    if bound_vargs:
        # from loguru import logger
        # logger.info(f"modified_sig:{self.modified_sig}")
        # logger.info(f"bound args:{bound_args}")
        # logger.info(f"call args:{args} kwargs:{kwargs}")
        varg_name = bound_vargs[0].name
        if varg_name in bound_args.arguments:
            new_args.extend(bound_args.arguments[varg_name])
    if bound_kwargs:
        vkwarg = bound_kwargs[0].name
        if vkwarg in bound_args.arguments:
            new_kwargs.update(bound_args.arguments[bound_kwargs[0].name])
    # logger.info(f"final args:{new_args}, kwarg:{new_kwargs}")
    return tuple(new_args), new_kwargs


@dataclass
class PartiallyInjectedFunction:
    """
    An object to be returned for @injected functions after provision.
    @injected
    def func(a,/,b):
        pass
    assert type(d.provide(func)) == PartiallyInjectedFunction
    """
    injected_params: dict
    name: str
    src_function: Callable
    final_sig: inspect.Signature
    func_sig: inspect.Signature

    def __post_init__(self):
        self.__name__ = self.name
        self.__signature__ = self.final_sig

    def __call__(self, *args, **kwargs):
        args, kwargs = get_final_args_kwargs(
            self.final_sig,
            self.func_sig,
            self.injected_params,
            *args,
            **kwargs
        )
        res = self.src_function(*args, **kwargs)
        return res


class Partial(Injected):

    def __init__(self,
                 src_function: Callable,
                 injection_targets: dict[str, Injected],
                 modifier: Optional[ArgsModifier] = None
                 ):
        self.src_function = src_function
        self.injection_targets = injection_targets
        self.func_sig = inspect.signature(self.src_function)
        self.modified_sig = self.get_modified_signature()
        self.injections = Injected.dict(**self.injection_targets).eval()
        self.__is_async_function__ = inspect.iscoroutinefunction(self.src_function)
        self.modifier = modifier
        self.dynamic_cache = dict()

    def get_modified_signature(self):
        params = self.func_sig.parameters.copy()
        for t in self.injection_targets.keys():
            del params[t]
        return inspect.Signature(parameters=list(params.values()))

    def final_args_kwargs(self, __injected__: dict, *args, **kwargs):
        return get_final_args_kwargs(
            self.modified_sig,
            self.func_sig,
            __injected__,
            *args,
            **kwargs
        )

    def call_with_injected(self, __injected__: dict, *args, **kwargs):
        args, kwargs = self.final_args_kwargs(__injected__, *args, **kwargs)
        res = self.src_function(*args, **kwargs)
        return res

    def get_provider(self):
        """
        Here we want to return a provider function that can return a injected function object.
        """

        return Injected.bind(
            self._provider_impl,
            __injected__=self.injections,
        ).get_provider()

    async def _provider_impl(self, __injected__: dict):
        return PartiallyInjectedFunction(
            injected_params=__injected__,
            name=self.src_function.__name__,
            src_function=self.src_function,
            final_sig=self.modified_sig,
            func_sig=self.func_sig
        )

    def dependencies(self) -> Set[str]:
        return self.injections.dependencies()

    def dynamic_dependencies(self) -> Set[str]:
        return self.injections.dynamic_dependencies()

    def __repr_expr__(self):
        return f"{self.src_function.__name__}<{self.injections.__repr_expr__()}>"

    def __call__(self, *args, **kwargs):
        if self.modifier is not None:
            args, kwargs, causes = self.modifier(args, kwargs)
            causes: list[Injected]
            dyn_deps = set()
            for c in causes:
                assert isinstance(c, (Injected, DelegatedVar)), f"causes:{causes} is not an Injected, but {type(c)}"
                if isinstance(c, DelegatedVar):
                    c = c.eval()
                dyn = c.dynamic_dependencies()
                assert isinstance(dyn, set), f"dyn:{dyn} is not a set"
                dyn_deps |= c.dynamic_dependencies()
            dyn_deps = frozenset(dyn_deps)

            if dyn_deps not in self.dynamic_cache:
                dyn_self = self.add_dynamic_dependencies(*dyn_deps)
                dyn_self.__is_async_function__ = self.__is_async_function__
                self.dynamic_cache[dyn_deps] = dyn_self
            dyn_self = self.dynamic_cache[dyn_deps]
            called = dyn_self.proxy(*args, **kwargs)
            return called
        return self.proxy(*args, **kwargs)
