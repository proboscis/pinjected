"""
Here i make a converter of a class.
1. adds __session__ as main attribute
2. replace original class's methods with injected versions.

"""
import inspect
from dataclasses import dataclass

from loguru import logger

from pinjected import Injected
from pinjected.di.implicit_globals import IMPLICIT_BINDINGS
from pinjected.di.partially_injected import Partial
from pinjected.injected_class.modify_ast_test import convert_cls
from pinjected.injected_class.test_module import PClassExample
from pinjected.v2.binds import BindInjected
from pinjected.v2.keys import StrBindKey


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


def convert_method_into_dynamic_injected_method(key: str, method):
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
    converted = convert_cls(cls, methods_to_convert=target_methods, attrs_to_replace=injected_attrs)
    converted = dataclass(converted)
    # make a new constructor to add __resolver__ as its attribute.
    injection_key = cls.__module__ + '.' + cls.__name__

    for name in target_methods:
        key = f"{injection_key}.{name}"
        setattr(converted, name, convert_method_into_dynamic_injected_method(
            key=key,
            method=getattr(converted, name)
        ))

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
    #IMPLICIT_BINDINGS[StrBindKey(f'new_{cls.__name__}')] = BindInjected(res)
    return res


async def main():
    from pinjected import design

    ModClass: Partial = pclass(PClassExample)
    d = design(
        dep=0,
        dep1=0
    )
    r = d.to_resolver()
    instance = (await r[ModClass])('a', 'b', 'c')
    logger.info(instance)
    logger.info(await instance.simple_method(0))
    logger.info(instance.method_with_dep1)
    logger.info(await instance.method_with_dep1(0))
    # logger.info(await instance.method1(1))


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
