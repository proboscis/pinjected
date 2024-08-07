import asyncio
import inspect
import sys
from dataclasses import dataclass
from functools import wraps

from loguru import logger

"""
Caching is an important feature for a pclass.

1. lazy property definition
- basically I want some methods to work as lazy property.
2. caching
- we want to memoize the computation on either memory or file.
- we want to control which method uses which cache.

-> @cached
- @cached
- @cached("__cache__") <- this tells which attribute of self to use for caching.
- @cached("__cache2__")

-> how do we set the cache attr?
  - I want it to be set via injection.
  - okey, so... we are not using the self's attr but using injected thing! okey.
  - but the namespace would deplete quickly.

  so we need to set like:
  example=pclass(Example)(
    file_cache=sqlite_dict('some_path'),
    memory_cache=dict(),
  )

  #Okey, but what about small classes?

  new_Race=Injected.partial(
    pclass(Race),
    file_cache=sqlite_dict('some_path'),
    memory_cache=dict(),
  )
  race = new_Race(rid)
  # this works, but tedious? but I guess it's fine:)
  So, let's implement this.
  I want this @cache to work with both pclass and normal class.
  I think this is just fine, since we can just wrap the method and access self.<cache>
"""


def get_class_from_unbound_method(method):
    full_name = method.__qualname__
    class_name = full_name.split('.')[0]
    return getattr(sys.modules[method.__module__], class_name)


def pcached(cache_attr_name, keys: set[str] = None):
    """
    This is a user interface function.
    First we need to determine what to use for caching.
    1. keys from self attribute.
    2. keys from method arguments.
    # Options:
    1. set of str: ['self.a','arg1','arg2']
    """

    def impl(method):
        return _pcached_impl(method, cache_attr_name, keys)

    return impl


def _pcached_impl(method, cache_attr_name, keys: set[str]):
    """
    Actual implementation where all required info is present here.
    """
    keys = set(keys)
    method_sig = inspect.signature(method)
    method_name = method.__name__
    logger.info(f"method:{method}")
    logger.info(f"method sig:{method_sig}")
    self_keys = {k.replace("self.", "") for k in keys if k.startswith('self.')}
    arg_keys = {k for k in keys if not k.startswith('self.')}
    assert inspect.iscoroutinefunction(method), f"Only async methods are supported. {method.__name__}"
    logger.info(f"arg keys:{arg_keys}")
    logger.info(f"self keys:{self_keys}")

    async def method_impl(self, *args, **kwargs):
        # hm, have args... we need to extract what we are interested in
        bound = method_sig.bind(self, *args, **kwargs)
        keys_from_args = tuple(bound.arguments[k] for k in arg_keys)
        keys_from_self = tuple(getattr(self, k) for k in self_keys)
        cache_key = method_name, keys_from_args, keys_from_self
        cache = getattr(self, cache_attr_name)

        if cache_key in cache:
            logger.info(f"cache hit for {cache_key}")
            return cache[cache_key]
        res = await method(self, *args, **kwargs)
        cache[cache_key] = res
        return res

    return wraps(method)(method_impl)


@dataclass
class ExampleClass:
    __cache__: dict
    a: str

    async def test_method(self, x):
        return self.a, x


class PClassExample:
    _dep1: str
    a: str
    cache: dict

    @pcached('cache', {'x'})
    async def test_method(self, x):
        return self._dep1, self.a, x


def test_dataclass_caching():
    cached = _pcached_impl(
        ExampleClass.test_method,
        '__cache__',
        {'self.a', 'x'}
    )
    ExampleClass.test_method = cached
    instance = ExampleClass(
        dict(),
        'value_a'
    )
    logger.info(cached)
    logger.info(asyncio.run(instance.test_method('value_x')))
    logger.info(asyncio.run(instance.test_method('value_x')))


def test_pclass_caching():
    async def impl():
        from pinjected import design, injected
        d = design(
            dep1="dep_1",
            my_cache=dict()
        )
        g = d.to_resolver()
        from pinjected.injected_class.injectable_class import pclass

        constructor = pclass(PClassExample)
        instance = await g[constructor(
            a="value_a",
            cache=injected('my_cache')
        )]
        logger.info(await instance.test_method('value_x'))
        logger.info(await instance.test_method('value_x'))

    return asyncio.run(impl())


if __name__ == '__main__':
    test_dataclass_caching()
    test_pclass_caching()
