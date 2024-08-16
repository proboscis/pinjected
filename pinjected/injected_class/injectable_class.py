"""
Here i make a converter of a class.
1. adds __session__ as main attribute
2. replace original class's methods with injected versions.

"""
import inspect
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from functools import wraps

from loguru import logger

from pinjected import Injected
from pinjected.compatibility.task_group import TaskGroup
from pinjected.di.partially_injected import Partial
from pinjected.injected_class.extract_self_attrs import extract_attribute_accesses
from pinjected.injected_class.test_module import PClassExample
from pinjected.v2.keys import StrBindKey
from pinjected.v2.resolver import AsyncResolver
import asyncio


@dataclass
class TargetClassSample:
    _dep1: str
    _dep2: int

    attr1: str
    attr2: int

    async def method1(self, args):
        return (self._dep1, args)


PLACEHOLDER = 'PLACEHOLDER'


class MacroTransformedExample:
    a: str
    b: int
    c: float

    def _method(self):
        return (self.a, self.b, self.c)

    def method1(self, x, __self_a__, __self_b__):
        def test_inner():
            return __self_a__ + str(__self_b__) + str(self.c)

        return __self_a__ + str(__self_b__) + str(self.c) + x

    def method2(self, y, __self_a__):
        return __self_a__ * y + str(self.c)


"""
Resulting class:
class TargetClassSample:
    __session__
    _dep1:str
    _dep2:int
    
    _method1
    async def method1(self,args):
        return await self._method1(args)
        
Steps.
1. add __session__
2. implement a way to create a 'injected' method implementation given a method.
3. use a name as method implementation

Question is how to specify the deps for a method.
1. class attributes
-> check ast for if self.attr is accessed. and the resolve it on function call.
replace add __self_attr__ to the func args and replace self.attr with __self_attr__.
This way, the func signature is preserved.


"""


def convert_method_into_dynamic_injected_method_old(key: str, method):
    signature = inspect.signature(method)
    assert inspect.iscoroutinefunction(method) or inspect.isasyncgenfunction(
        method), f"method:{method} must be async to be converted."
    assert 'self' in signature.parameters.keys()
    logger.info(f"method parameters:{signature.parameters.keys()}")
    logger.info(f"converting method:{method}")
    targets = [
        p for p in signature.parameters.keys() if
        p.startswith("__self_") and p != 'self'
    ]
    logger.info(f"positionals:{targets}")

    internal_method_impl = Injected.inject_partially(
        original_function=method,
        **{d: Injected.dynamic(d.replace('__self__', "")[:-2]) for d in targets}
    )
    from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
    from pinjected.v2.binds import BindInjected
    IMPLICIT_BINDINGS[StrBindKey(key)] = BindInjected(
        internal_method_impl
    )

    async def replaced_method(self, *args, **kwargs):
        impl = await self.__resolver__[key]
        return await impl(self, *args, **kwargs)

    # replaced_method.__signature__ = signature

    return wraps(method)(replaced_method)
    # return replaced_method


@dataclass
class InjectedMethod:
    dynamic_attr_mapping: dict[str, Injected]  # attr_name to injection_key
    method: callable
    resolver: AsyncResolver

    def __post_init__(self):
        self.method_init_lock = asyncio.Lock()
        self.method_init_key = "__" + self.method.__name__ + "_initialized__"
        self.__signature__ = inspect.signature(self.method)

    async def assign_task(self, tgt_self, attr_name, dep: Injected):
        if getattr(tgt_self, attr_name) == PLACEHOLDER:
            setattr(tgt_self, attr_name, await self.resolver[dep])

    async def init_self_attrs(self, tgt_self):
        async with self.method_init_lock:
            if not getattr(tgt_self, self.method_init_key, False):
                async with TaskGroup() as tg:
                    for attr_name, dep in self.dynamic_attr_mapping.items():
                        tg.create_task(self.assign_task(tgt_self, attr_name, dep))
                    setattr(tgt_self, self.method_init_key, True)

    async def __call__(myself, self, *args, **kwargs):
        await myself.init_self_attrs(self)
        return await myself.method(self, *args, **kwargs)


def convert_method_into_dynamic_injected_method(key: str, method, dynamic_deps_mapping: dict[str, Injected]):
    signature = inspect.signature(method)
    if not (inspect.iscoroutinefunction(method) or inspect.isasyncgenfunction(method)):
        logger.warning(f"method:{method} is not async method. double check if it's asynccontextmanager")

    assert 'self' in signature.parameters.keys()
    logger.info(f"method parameters:{signature.parameters.keys()}")
    logger.info(f"converting method:{method}")
    targets = [
        p for p in signature.parameters.keys() if
        p.startswith("__self_") and p != 'self'
    ]
    logger.info(f"positionals:{targets}")

    internal_method_impl = Injected.bind(
        InjectedMethod,
        dynamic_attr_mapping=Injected.pure(dynamic_deps_mapping),
        method=Injected.pure(method),
        resolver=Injected.by_name('__resolver__')
    )

    from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
    from pinjected.v2.binds import BindInjected
    IMPLICIT_BINDINGS[StrBindKey(key)] = BindInjected(
        internal_method_impl
    )
    method_injection_key = '__' + method.__name__ + '_injected__'

    async def replaced_method(self, *args, **kwargs):
        if getattr(self, method_injection_key, None) is None:
            setattr(self, method_injection_key, await self.__resolver__[key])
        impl = getattr(self, method_injection_key)
        return await impl(self, *args, **kwargs)

    return replaced_method


def pclass(cls):
    """
    1. find methods with deps
    2. create impls
    3. make a new constructor to accept impls + session
    4. replace original methods with impls\
    """
    #
    injected_attrs = [v for v in cls.__annotations__ if v.startswith('_')]
    logger.info(f"injectable attrs:{injected_attrs}")
    target_methods = []
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        src = inspect.getsource(method)
        logger.info(f"method src:\n{src}")
        for attr in injected_attrs:
            logger.info(f"checking attr:{attr}")
            if attr in src:
                target_methods.append(name)
                break
    logger.info(f"target methods:{target_methods}")
    # now we can convert the class ast:
    # converted = convert_cls(cls, methods_to_convert=target_methods, attrs_to_replace=injected_attrs)

    attribute_accesses = extract_attribute_accesses(cls)
    for method_name in attribute_accesses:
        setattr(cls, method_name, convert_method_into_dynamic_injected_method(
            key=f"{cls.__module__}.{cls.__name__}.{method_name}",
            method=getattr(cls, method_name),
            dynamic_deps_mapping={attr: Injected.by_name(attr[1:]) for attr in attribute_accesses[method_name]}
        ))

    converted = dataclass(cls)
    # make a new constructor to add __resolver__ as its attribute.

    injected_constructor = Injected.inject_partially(
        converted,
        **{d: Injected.pure(PLACEHOLDER) for d in injected_attrs}
    )

    def constructor_with_resolver(
            __resolver__,
            constructor,
            *args,
            **kwargs
    ):
        self = constructor(*args, **kwargs)
        self.__resolver__ = __resolver__
        return self

    res = Injected.inject_partially(
        constructor_with_resolver,
        constructor=injected_constructor,
        __resolver__=Injected.by_name('__resolver__')
    )
    # IMPLICIT_BINDINGS[StrBindKey(f'new_{cls.__name__}')] = BindInjected(res)
    return res


async def main():
    from pinjected import design

    ModClass: Partial = pclass(PClassExample)
    d = design(
        dep=0,
        dep1="dep1_value"
    )
    r = d.to_resolver()
    instance = (await r[ModClass])('a', 'b', 'c')
    logger.info(instance)
    logger.info(await instance.simple_method(0))
    logger.info(instance.method_with_dep1)
    logger.info(await instance.method_with_dep1('x_value'))
    # logger.info(await instance.method1(1))


"""
After making this pclass, I realized that it is not a good idea to introduce classes...

Well, for internal use, we can be very happy with it.
But.. for example, if you implement POpenAI class with bunch of util functions,
you need to import it and depend on it. 
However, the actual dependency is only one function like 'a_vision_llm'
So, the user side should not depend on specific class that is outside of the module...

I mean, if it's like

def _play_with_llm(api:POpenAI,/,prompt):
    return api.a_vision_llm(prompt)
    pass
    
you need to import POpenAI! and api must have a_vision_llm.

Instead, we could just write

def _play_with_llm(a_vision_llm,/,prompt):
    return a_vision_llm(prompt)
    
and the user side can just inject a_vision_llm.

hmm.

Alright, so you shouldn't be using the class it self as a dependency, unless it's required.
However, we want to know what we are expecting as dependencies.
For that purpose, you could use typing.

def play_with_llm(
        llm:Annotated[LLM,InjectionKeys.VisionLLM],
        prompt
    ):
    return llm(prompt)
    
Now, llm gets injected. also, the key can be auto-completed from InjectionKeys....
However,,, now i need to manage the keys...

Somehow we need to manage the available keys to be injected

What was it like to live without injection?
-> So many confusing initializations and manual constructions, causing spaghetti code.
Now, we have a clear dependency tree, and we can easily see what is required to be injected.
However, it is harder to see what we can request.
For example in bodai_bakyo, I have no idea what i can request. 

So, use pclass for internal data modeling! 
use injected functions for external exposure! 
It's much simpler.
"""

if __name__ == '__main__':
    asyncio.run(main())
