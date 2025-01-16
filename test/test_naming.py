import pytest
from pinjected.di.partially_injected import PartiallyInjectedFunction


def test_naming_convention_for_injected_function():
    from pinjected import injected, design
    from loguru import logger
    @injected
    def target_function(x, /, y, z):
        pass

    d = design(
        x=0
    )
    func = d.provide(target_function)
    logger.info(f"Function name: {func.__name__}")
    assert type(
        func) == PartiallyInjectedFunction, f"@injected function must return PartiallyInjectedFunction after resolution, got {type(func)}"


def test_lambda_functions_in_bind():
    """Test that lambda functions are allowed in Injected.bind but not in @injected decorator."""
    from pinjected import injected, Injected
    from pinjected.di.util import instances

    # Test lambda in Injected.bind - should work
    bound = Injected.bind(lambda x: x + 1)
    g = instances(x=1).to_graph()
    assert g[bound] == 2

    # Test lambda in @injected decorator - should raise error
    with pytest.raises(ValueError, match="Lambda or anonymous functions are not supported with @injected decorator"):
        @injected
        def wrapper():
            return lambda x: x + 1


def test_unnamed_functions():
    """Test that functions without __name__ attribute are not allowed in @injected."""
    from pinjected import injected, Injected
    from pinjected.di.util import instances

    # Create a function without __name__
    def make_unnamed():
        f = lambda x: x + 1
        delattr(f, "__name__")  # Force remove name
        return f

    # Test in Injected.bind - should work
    unnamed = make_unnamed()
    bound = Injected.bind(unnamed)
    g = instances(x=1).to_graph()
    assert g[bound] == 2

    # Test in @injected decorator - should raise error
    with pytest.raises(ValueError, match="Cannot register a function without a proper name in the global registry"):
        @injected
        def wrapper():
            return make_unnamed()
