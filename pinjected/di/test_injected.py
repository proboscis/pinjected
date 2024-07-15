import inspect

from pinjected import injected_function, injected
from pinjected.di.injected import Injected
from pinjected.di.util import instances, EmptyDesign


def _factory(a, b, y=0, x=7):
    assert a == 3
    assert b == 2
    assert x == 5
    return a + b + x


def test_partial():
    d = EmptyDesign.bind_instance(
        a=1,
        b=2
    ).bind_provider(
        f=Injected.inject_partially(_factory, b=Injected.by_name("b"), x=Injected.pure(5))
    )
    assert d.provide("f")(3) == 10


def test_injected_function():
    @injected_function
    def test_func(_x, _y, /, *args, **mykwargs):
        assert args, "args should be non-empty"
        return _x + _y + str(args)

    g = instances(
        x='x',
        y='y',
    ).to_resolver().to_blocking()
    assert g[test_func](1, 2, 3, 5, 6) == 'x' + 'y' + '(1, 2, 3, 5, 6)'

class FunctionWrapper:
    def __init__(self, func):
        self.func = func
        self.signature = inspect.signature(func)

    def __call__(self, *args, **kwargs):
        bound_args = self.signature.bind(*args, **kwargs)
        bound_args.apply_defaults()

        positional_args = [bound_args.arguments[param.name] for param in self.signature.parameters.values() if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)]
        var_positional_args = bound_args.arguments.get(next((param.name for param in self.signature.parameters.values() if param.kind == inspect.Parameter.VAR_POSITIONAL), None), ())
        keyword_args = {param.name: bound_args.arguments[param.name] for param in self.signature.parameters.values() if param.kind == inspect.Parameter.KEYWORD_ONLY}
        var_keyword_args = bound_args.arguments.get(next((param.name for param in self.signature.parameters.values() if param.kind == inspect.Parameter.VAR_KEYWORD), None), {})

        return self.func(*positional_args, *var_positional_args, **keyword_args, **var_keyword_args)

# Test functions with different signatures
def _test_function1(a, b, /, c, *args, d=10, **kwargs):
    assert a == 1
    assert b == 2
    assert c == 3
    assert args == (4, 5)
    assert d == 10
    assert kwargs == {'x': 7, 'y': 8}


def _test_function2(a, b, /, c, *args, d=10, e, f=20, **kwargs):
    assert a == 1
    assert b == 2
    assert c == 3
    assert args == (4, 5)
    assert d == 10
    assert e == 6
    assert f == 20
    assert kwargs == {'x': 7, 'y': 8}


def _test_function3(*, a, b):
    assert a == 1
    assert b == 2


def _test_function4(a, b, c=3, *, d, e=5):
    assert a == 1
    assert b == 2
    assert c == 3
    assert d == 4
    assert e == 5


# Pytest test cases
def test_function_wrapper():
    wrapped_func1 = FunctionWrapper(_test_function1)
    wrapped_func1(1, 2, 3, 4, 5, x=7, y=8)

    wrapped_func2 = FunctionWrapper(_test_function2)
    wrapped_func2(1, 2, 3, 4, 5, e=6, x=7, y=8)

    wrapped_func3 = FunctionWrapper(_test_function3)
    wrapped_func3(a=1, b=2)

    wrapped_func4 = FunctionWrapper(_test_function4)
    wrapped_func4(1, 2, d=4)


def test_injected_function_with_defaults():
    def test_pure_func(x, y, /, a, b, *args, z=7, **mykwargs):
        return x, y, (a, b, *args), mykwargs, z

    @injected
    def test_func(x, y, /, a, b, *args, z=7, **mykwargs):
        return x, y, (a, b, *args), mykwargs, z

    @injected
    def test_func2(_x, _y, a, b, z=7, s=10):
        return _x, _y, (a, b), z, s

    g = instances(
        x='x',
        y='y',
    ).to_graph()
    expectation = ("x", 'y', (1, 2, 3, 5, 6), {}, 7)
    expectation2 = ("x", 'y', (1, 2, 3, 5, 6), {}, 9)
    expectation3 = ("x", 'y', (1, 2, 3, 5, 6), {'p': 42}, 7)
    expectation4 = ("x", 'y', (1, 2, 3, 5, 6), {'p': 42}, 9)
    expectation5 = ("x", 'y', (1, 2), {}, 7)
    expectation6 = ("x", 'y', (1, 2), 7, 10)
    assert test_pure_func('x', 'y', 1, 2, 3, 5, 6) == expectation
    assert g[test_func(1, 2, 3, 5, 6)] == expectation
    assert g[test_func](1, 2, 3, 5, 6) == expectation
    # This error is caused by,, the fact that named args passes as positional are converted to kwargs internally.
    # So, Call object must remember the exact call style it is invoked.
    # This becomes like this. but not correct. it should be 1,2,3,5,6.
    # InjectedWithDynamicDependencies(test_func<injected_kwargs=<<class 'dict'>>(x=$x,y=$y)>(3,5,6,a=1,b=2,z=7), set())
    assert g[test_func](1, 2, 3, 5, 6, z=9) == expectation2
    assert g[test_func(1, 2, 3, 5, 6, z=9)] == expectation2
    assert g[test_func(1, 2, 3, 5, 6, p=42)] == expectation3
    assert g[test_func](1, 2, 3, 5, 6, p=42) == expectation3
    assert g[test_func](1, 2, 3, 5, 6, p=42, z=9) == expectation4
    assert g[test_func(1, 2, 3, 5, 6, p=42, z=9)] == expectation4
    assert g[test_func(1, 2)] == expectation5
    assert g[test_func](1, 2) == expectation5
    assert g[test_func2](1, 2) == expectation6
    assert g[test_func2(1, 2)] == expectation6
    assert g[test_func2(1, 2, 7)] == expectation6

if __name__ == '__main__':
    pass