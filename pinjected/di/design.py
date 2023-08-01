import inspect
from functools import wraps
from typing import TypeVar, List

from makefun import create_function

from pinjected.di.injected import extract_dependency_including_self

T = TypeVar("T")
U = TypeVar("U")


def map_wrap(src, f):
    @wraps(src)
    def wrapper(*args, **kwargs):
        return f(src(*args, **kwargs))

    wrapper.__signature__ = inspect.signature(src)
    return wrapper


def remove_kwargs_from_func(f, kwargs: List[str]):
    deps = extract_dependency_including_self(f)
    to_remove = set(kwargs)
    new_kwargs = deps - to_remove
    func_name = f.__name__.replace("<lambda>", "_lambda_")
    sig = f"""{func_name}({",".join(new_kwargs)})"""

    def impl(**called_kwargs):
        deleted = deps & to_remove
        # for self, you must check whether f is method or not
        if inspect.ismethod(f):
            deleted = deleted - {"self"}
        d_kwargs = {k: None for k in deleted}
        return f(**called_kwargs, **d_kwargs)

    return create_function(sig, impl)
