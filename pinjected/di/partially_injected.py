import inspect
from typing import Callable, Set

from pinjected import Injected
from pinjected.di.injected import DictInjected


class Partial(Injected):

    def __init__(self, src_function: Callable, injection_targets: dict[str, Injected]):
        self.src_function = src_function
        self.injection_targets = injection_targets
        self.func_sig = inspect.signature(self.src_function)
        self.modified_sig = self.get_modified_signature()
        self.injections = DictInjected(**self.injection_targets)
        self.__is_async_function__ = inspect.iscoroutinefunction(self.src_function)

    def get_modified_signature(self):
        params = self.func_sig.parameters.copy()
        for t in self.injection_targets.keys():
            del params[t]
        return inspect.Signature(parameters=list(params.values()))

    def final_args_kwargs(self, __injected__: dict, *args, **kwargs):
        """
        the target cannot be VAR_POSITIONAL or VAR_KEYWORD, i.e. *args, **kwargs

        iterate through original signature, and replace the injected targets with the provided values.
        the injected values may be Postional only, Positional or Keyword, or Keyword only. so we need to split them.
        """
        bound_args = self.modified_sig.bind(*args, **kwargs)
        new_args = []
        new_kwargs = {}

        def add_by_type(param, value):
            if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                new_args.append(value)
            elif param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                new_args.append(value)
            elif param.kind == inspect.Parameter.KEYWORD_ONLY:
                new_kwargs[param.name] = value

        for param in self.func_sig.parameters.values():
            if param.name in self.injection_targets:
                add_by_type(param, __injected__[param.name])
            else:
                if param.name in bound_args.arguments:
                    add_by_type(param, bound_args.arguments[param.name])
        bound_vargs = [varg for varg in self.modified_sig.parameters.values() if
                       varg.kind == inspect.Parameter.VAR_POSITIONAL]
        bound_kwargs = [varg for varg in self.modified_sig.parameters.values() if
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
        return tuple(new_args), new_kwargs

    def call_with_injected(self, __injected__: dict, *args, **kwargs):
        args, kwargs = self.final_args_kwargs(__injected__, *args, **kwargs)
        res = self.src_function(*args, **kwargs)
        return res

    def get_provider(self):
        """
        def example(pos_only, /, normal, *args, kw_only, **kwargs):
            pass
        inspect.Parameter.POSITIONAL_ONLY -> pos_only
        "/"
        inspect.Parameter.POSITIONAL_OR_KEYWORD -> normal
        inspect.Parameter.VAR_POSITIONAL -> args
        "* or *args"
        inspect.Parameter.KEYWORD_ONLY -> kw_only
        inspect.Parameter.VAR_KEYWORD -> kwargs

        Now, I want to replace the args in injection_targets to become
        the first positional only arg:__injected__:dict
        and keep the rest to be same
        """

        async def impl(__injected__: dict):
            def inner_impl(*args, **kwargs):
                return self.call_with_injected(__injected__, *args, **kwargs)

            return inner_impl

        return Injected.bind(
            impl,
            __injected__=self.injections,
        ).get_provider()

    def dependencies(self) -> Set[str]:
        return self.injections.dependencies()

    def dynamic_dependencies(self) -> Set[str]:
        return self.injections.dynamic_dependencies()

    def __repr_expr__(self):
        return f"{self.src_function.__name__}<{self.injections.__repr_expr__()}>"

    def __call__(self, *args, **kwargs):
        return self.proxy(*args, **kwargs)
