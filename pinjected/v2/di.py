import asyncio
from dataclasses import dataclass
from typing import Generic, TypeVar, Dict, Callable, Awaitable, Union

from loguru import logger

from pinjected import Injected, Design
from pinjected.v2.binds import IBind, StrBind
from pinjected.v2.keys import IBindKey, StrBindKey
from pinjected.v2.resolver import AsyncResolver

# from pinjected import Injected, Design, injected, instance
# from pinjected import instances as d_instances
# from pinjected import providers as d_providers
# from pinjected.di.implicit_globals import IMPLICIT_BINDINGS

T = TypeVar('T')
U = TypeVar('U')


class _Injected(Generic[T]):
    """

    """


@dataclass(frozen=True)
class Blueprint:
    bindings: Dict[IBindKey, IBind]

    def __add__(self, other):
        match other:
            case Design():
                return self + design_to_blueprint(other)
            case Blueprint():
                return Blueprint(self.bindings | other.bindings)
            case _:
                raise TypeError(f"Blueprint can only be added with Blueprint or Design, got {other}")

    def blocking_resolver(self):
        return AsyncResolver(self).to_blocking()

    def async_resolver(self):
        return AsyncResolver(self)


def instances(**kwargs):
    return Blueprint({StrBindKey(k): StrBind.pure(v) for k, v in kwargs.items()})


def providers(**kwargs: Callable[..., Union[T, Awaitable[T]]]):
    return Blueprint({StrBindKey(k): StrBind.bind(v) for k, v in kwargs.items()})


def injected_to_str_bind(injected: Injected):
    match injected:
        case object(__is_awaitable__=True):
            return StrBind.async_bind(injected.get_provider())
        case x:
            return StrBind.bind(injected.get_provider())


def design_to_blueprint(design: Design):
    bindings = IMPLICIT_BINDINGS | design.bindings
    return Blueprint({StrBindKey(k): injected_to_str_bind(v.to_injected()) for k, v in bindings.items()})


# %%
"""
TODO make blueprint from a design
by default ,convert the Injected into async func.
"""


@instance
async def slow_1():
    logger.info(f"running slow_1")
    await asyncio.sleep(1)
    logger.info(f"slow_1 done")
    return 1


@instance
async def slow_data():
    logger.info(f"running slow_data")
    await asyncio.sleep(1)
    logger.info(f"slow_data done")
    return 1


@instance
async def slow_calc(slow_data, slow_1):
    return slow_data + slow_1


@instance
def blocking_x(slow_data, slow_1):
    return slow_data + slow_1


bp = providers(
) + d_instances(
    x='x',
    y='y'
) + d_providers(
    slow_1=slow_1,
    slow_data=slow_data
)


# we can use async_bind on @instance to make it work.
async def wait(t):
    return await t


bp.blocking_resolver().provide('blocking_x')
# %%
# In order to fully switch to async design, I need to ...
"""
1. implement visualizer -> 3 hours
2. implement partial injection annotator -> 3 hours
3. implement run_main with meta-design -> 1 day
4. implement plugins  -> 3 hours
-> total 2 days of work. hmm....

Wait isnt this already done???
You can just use the Injected, you implemented already.
Right, and call async_resolver().provide() to get the result.
"""
