import inspect
from types import FunctionType
from typing import Union, Type, Callable, TypeVar

from makefun import create_function
from pinject.object_graph import ObjectGraph

from pinject_design.di.injected import Injected

T = TypeVar("T")
class ExtendedObjectGraph:
    """
    an object graph which can also provide instances based on its name not only from class object.
    """

    def __init__(self, design: "Design", src: ObjectGraph):
        self.design = design
        self.src = src

    def provide(self, target: Union[str, Type[T], Injected[T], Callable]) -> Union[object, T]:
        if isinstance(target, str):
            assert target!="self", f"provide target:{target}"
            code = compile(f"""def __init__(self,{target}):self.res={target}""", "<string>", "exec")
            fn = FunctionType(code.co_consts[0], globals(), "__init__")
            Request = type("Request", (object,), dict(__init__=fn))
            return self.src.provide(Request).res
        elif isinstance(target, type):
            return self.src.provide(target)
        elif isinstance(target, Injected):
            deps = target.dependencies()
            if 'self' in deps:
                deps.remove('self')
            signature = f"""__init__(self,{','.join(deps)})"""

            def impl(self, **kwargs):
                self.data = target.get_provider()(**kwargs)

            __init__ = create_function(signature, func_impl=impl)
            Request = type("Request", (object,), dict(__init__=__init__))
            return self.src.provide(Request).data
        elif isinstance(target, Callable):
            return self.run(target)
        else:
            raise TypeError(f"target must be either class or a string or Injected. got {target}")

    def run(self, f):
        argspec = inspect.getfullargspec(f)
        assert "self" not in argspec.args, f"self in {argspec.args}, of {f}"
        # logger.info(self)
        assert argspec.varargs is None
        kwargs = {k:self.provide(k) for k in argspec.args}
        return f(**kwargs)

    def __repr__(self):
        return f"ExtendedObjectGraph of a design:\n{self.design}"