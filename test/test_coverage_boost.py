"""Simple tests to boost coverage for core modules."""

import pytest
from pinjected import (
    design,
    instance,
    injected,
    Injected,
    classes,
    instances,
    providers,
)
from pinjected.di.proxiable import DelegatedVar
from pinjected.di.util import extract_argnames, get_class_aware_args
from pinjected.di.args_modifier import KeepArgsPure
from pinjected.di.design import DesignImpl, MergedDesign
from pinjected.v2.keys import StrBindKey
from pinjected.v2.binds import BindInjected


def test_injected_more_operations():
    """Test more Injected operations for coverage."""

    # Test dependencies extraction
    def my_func(a, b, c=10):
        return a + b + c

    inj = Injected.bind(my_func)
    deps = inj.dependencies()
    assert "a" in deps
    assert "b" in deps
    assert "c" in deps

    # Test with defaults provided
    d = design(a=1, b=2, c=3)
    assert d.provide(inj) == 6

    # Test ensure_injected
    already_injected = Injected.by_name("test")
    assert Injected.ensure_injected(already_injected) == already_injected

    # ensure_injected converts strings and callables
    str_injected = Injected.ensure_injected("test_value")
    assert isinstance(str_injected, Injected)

    def my_func():
        return 42

    func_injected = Injected.ensure_injected(my_func)
    assert isinstance(func_injected, Injected)
    assert d.provide(func_injected) == 42


def test_design_internals():
    """Test design internal operations."""
    # Create DesignImpl directly
    impl = DesignImpl()

    # Add bindings
    impl._bindings[StrBindKey("test")] = BindInjected(Injected.pure("value"))

    # Test binding access
    assert StrBindKey("test") in impl
    assert impl.provide("test") == "value"

    # Test from_bindings
    bindings = {
        StrBindKey("a"): BindInjected(Injected.pure(1)),
        StrBindKey("b"): BindInjected(Injected.pure(2)),
    }
    d = DesignImpl.from_bindings(bindings)
    assert d.provide("a") == 1
    assert d.provide("b") == 2


def test_merged_design():
    """Test MergedDesign functionality."""
    d1 = design(a=1, b=2)
    d2 = design(b=20, c=30)
    d3 = design(c=300, d=400)

    # Multiple merges
    merged = d1 + d2 + d3

    assert isinstance(merged, MergedDesign)
    assert len(merged.srcs) > 0

    # Values from later designs override
    assert merged.provide("a") == 1
    assert merged.provide("b") == 20
    assert merged.provide("c") == 300
    assert merged.provide("d") == 400


def test_util_functions_coverage():
    """Test utility functions for coverage."""

    # extract_argnames
    def func1(x, y, z):
        pass

    args = extract_argnames(func1)
    assert args == ["x", "y", "z"]

    # get_class_aware_args
    class MyClass:
        def __init__(self, a, b):
            pass

    # For classes, self is handled
    args = get_class_aware_args(MyClass)
    assert "self" not in args  # Should be removed
    assert "a" in args
    assert "b" in args


def test_args_modifier_coverage():
    """Test ArgsModifier for coverage."""
    import inspect

    def test_func(a, b, c):
        return a + b + c

    sig = inspect.signature(test_func)
    # KeepArgsPure requires signature and targets
    modifier = KeepArgsPure(signature=sig, targets=["a", "b"])

    # Test that it exists and can be instantiated
    assert modifier is not None


def test_providers_helper_coverage():
    """Test providers helper function."""

    def provide_sum(a, b):
        return a + b

    def provide_product(x, y):
        return x * y

    d = design(a=5, b=10, x=3, y=4) + providers(
        sum=provide_sum, product=provide_product
    )

    assert d.provide("sum") == 15
    assert d.provide("product") == 12


def test_classes_helper_coverage():
    """Test classes helper function."""

    class Service:
        def __init__(self, config):
            self.config = config

        def get_info(self):
            return f"Service: {self.config}"

    class Repository:
        def __init__(self, service):
            self.service = service

    d = design(config="test_config") + classes(service=Service, repository=Repository)

    repo = d.provide("repository")
    assert repo.service.get_info() == "Service: test_config"


def test_instances_helper_coverage():
    """Test instances helper function."""
    d = instances(string="hello", number=42, list=[1, 2, 3], dict={"key": "value"})

    assert d.provide("string") == "hello"
    assert d.provide("number") == 42
    assert d.provide("list") == [1, 2, 3]
    assert d.provide("dict") == {"key": "value"}


def test_delegated_var_operations():
    """Test DelegatedVar operations."""
    # Create through Injected
    base = Injected.by_name("value")
    proxy = base.proxy

    assert isinstance(proxy, DelegatedVar)

    # Test operations
    # Addition
    added = proxy + 10

    # Multiplication
    multiplied = proxy * 2

    d = design(value=5)
    assert d.provide(added) == 15
    assert d.provide(multiplied) == 10

    # Test proxy with string attribute
    class Obj:
        def __init__(self, val):
            self.value = val

    obj_injected = Injected.by_name("obj")
    value_proxy = obj_injected.proxy.value

    d2 = design(obj=Obj("test_value"))
    assert d2.provide(value_proxy) == "test_value"


def test_injected_either():
    """Test either/or dependency patterns."""
    # Create primary and fallback
    primary = Injected.by_name("primary")
    Injected.pure("default_value")

    # Use map to implement either logic
    def get_or_default(value):
        return value if value is not None else "default_value"

    either = primary.map(get_or_default)

    # With primary
    d1 = design(primary="main_value")
    assert d1.provide(either) == "main_value"

    # Without primary would fail, but we can handle in provider


def test_injected_dict_advanced():
    """Test advanced dict operations."""
    # Nested dict
    config = Injected.dict(
        database=Injected.dict(
            host=Injected.by_name("db_host"), port=Injected.by_name("db_port")
        ),
        cache=Injected.dict(
            type=Injected.pure("redis"), ttl=Injected.by_name("cache_ttl")
        ),
    )

    d = design(db_host="localhost", db_port=5432, cache_ttl=3600)

    result = d.provide(config)
    assert result["database"]["host"] == "localhost"
    assert result["database"]["port"] == 5432
    assert result["cache"]["type"] == "redis"
    assert result["cache"]["ttl"] == 3600


def test_injected_list_advanced():
    """Test advanced list operations."""
    # List with mixed types
    items = Injected.list(
        Injected.pure(1), Injected.by_name("item"), Injected.bind(lambda x: x * 2)
    )

    d = design(item="middle", x=5)
    result = d.provide(items)

    assert result[0] == 1
    assert result[1] == "middle"
    assert result[2] == 10


def test_complex_provider_chains():
    """Test complex provider dependency chains."""

    @instance
    def config():
        return {"debug": True, "timeout": 30}

    @instance
    def logger(config):
        level = "DEBUG" if config["debug"] else "INFO"
        return f"Logger({level})"

    @instance
    def database(config, logger):
        return f"DB(timeout={config['timeout']}, logger={logger})"

    @instance
    def cache(logger):
        return f"Cache(logger={logger})"

    @instance
    def repository(database, cache):
        return f"Repo({database}, {cache})"

    @instance
    def service(repository, logger):
        return f"Service({repository}, {logger})"

    d = design()
    result = d.provide(service)

    # Should resolve entire chain
    assert "Service(" in result
    assert "Repo(" in result
    assert "DB(" in result
    assert "Cache(" in result
    assert "Logger(DEBUG)" in result


def test_design_keys_method():
    """Test design.keys() method."""
    d = design(a=1, b=2, c=3)

    keys = list(d.keys())
    assert len(keys) >= 3

    # Keys should be StrBindKey instances
    assert any(k == StrBindKey("a") for k in keys)
    assert any(k == StrBindKey("b") for k in keys)


def test_design_empty():
    """Test empty design creation."""
    empty = DesignImpl.empty()

    assert isinstance(empty, DesignImpl)

    # Should have no user bindings (might have implicit ones)
    bindings = empty.bindings
    user_keys = [k for k in bindings if not str(k).startswith("__")]
    assert len(user_keys) == 0


def test_injected_proxy_attribute_chain():
    """Test chained attribute access through proxy."""

    class Level3:
        value = "deep_value"

    class Level2:
        level3 = Level3()

    class Level1:
        level2 = Level2()

    # Use proxy for chained attribute access
    obj_injected = Injected.by_name("deep_object")
    deep_value = obj_injected.proxy.level2.level3.value

    d = design(deep_object=Level1())
    assert d.provide(deep_value) == "deep_value"


def test_injected_with_injected_params():
    """Test @injected with other @injected as parameters."""

    @injected
    def processor(prefix, /, data: str) -> str:
        return f"{prefix}: {data}"

    @injected
    def wrapper(processor, suffix, /, text: str) -> str:
        # processor is an @injected function
        processed = processor(text)
        return f"{processed} {suffix}"

    d = design(prefix="START", suffix="END")
    wrap_func = d.provide(wrapper)

    result = wrap_func("hello")
    assert result == "START: hello END"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
