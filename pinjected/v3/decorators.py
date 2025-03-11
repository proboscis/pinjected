from functools import wraps
from typing import Concatenate, Callable, TypedDict, ParamSpec, TypeVar, Awaitable

from IPython.conftest import inject

from pinjected import IProxy

Dep = TypeVar("Dep", bound=TypedDict)
P = ParamSpec("P")
R = TypeVar("R")


# what about this?
def Inject(name: str):
    return name


# def function_proxy(f: Callable[P, R]) -> Callable[[P], IProxy[R]]:
#     return f

def function_proxy(f: Callable[P, R]) -> Callable[P, IProxy[R]]:
    return f


@function_proxy
def test_func_proxy(
        arg: int,
        dep1: int = Inject('dep1'),
        dep2: int = Inject('dep2')) -> int:
    pass


# this is understandable
y = test_func_proxy(0)

from typing import Callable, ParamSpec, TypeVar, Generic
import inspect
from functools import wraps

P = ParamSpec("P")
R = TypeVar("R")


class Inject:
    def __init__(self, name: str):
        self.name = name


# class IProxy(Generic[R]):
#     def __init__(self, value: R):
#         self.value = value

def function_proxy(f: Callable[P, R]) -> Callable[P, IProxy[R]]:
    sig = inspect.signature(f)

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> IProxy[R]:
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()

        # Inject dependencies
        for param_name, param in sig.parameters.items():
            if isinstance(param.default, Inject):
                if param_name not in bound.arguments or bound.arguments[param_name] is param.default:
                    bound.arguments[param_name] = resolve_dependency(param.default.name)

        result = f(*bound.args, **bound.kwargs)
        return IProxy(result)

    return wrapper


def resolve_dependency(name: str):
    deps = {
        'dep1': 10,
        'dep2': 20
    }
    return deps[name]


@function_proxy
def test_func_proxy(
        arg: int,
        # dep1: int = Inject('dep1'),
        dep1: int = 0,
        dep2: int = Inject('dep2')) -> int:
    print(f"{arg=}, {dep1=}, {dep2=}")
    return arg + dep1 + dep2


# IDE sees clearly: test_func_proxy(arg: int, dep1: int = ..., dep2: int = ...) -> IProxy[int]
def to_proxy(cls) -> IProxy:
    pass


@to_proxy
class InjectedService:
    dep1: int = Inject('dep1')
    dep2: str = Inject('dep2')

    def __call__(self, arg1, arg2):
        pass

@to_proxy
class InjectedServiceUser:
    dep:InjectedService = Inject('injected_service')
    dep_flag:bool = Inject('injected_flag')

    def __call__(self):
        # do stuff with dep and dep_flag
        pass

@to_proxy
class InjectedData:
    text:str
    dep_service:InjectedService = Inject('injected_service')

    def do_something(self):
        # do stuff with text and dep_service
        pass

some_result:IProxy  = InjectedData(text="hello").do_something()
p_service: IProxy = InjectedService()

# from now on we should be using type as key?
@to_proxy
class OpenRouterSLLM:
    impl_function:Callable[[str,],Awaitable[str]] = Inject('a_openrouter_chat_completion')
    async def __call__(self, request):
        pass

# ah, but now this is harder to apply partial application
# also, it is harder to add caching.
# then what can we do?
# I reali
"""
Current specific problem:

LLM writes @injected function.
Then pylance gives false messages to the user.
The LLM gets confuses and stuck in a loop.
Options:
1. fix library side so pylance dont get confused
2. fix pylance to not get confused
3. instruct LLM so much


"""

