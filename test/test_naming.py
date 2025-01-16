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


def test_lambda_functions_not_allowed():
    """Test that lambda functions are not allowed in @injected decorator and Injected.bind."""
    from pinjected import injected, Injected

    # Test lambda in Injected.bind
    with pytest.raises(ValueError, match="Lambda or anonymous functions are not supported"):
        Injected.bind(lambda x: x + 1)

    # Test lambda in @injected decorator
    with pytest.raises(ValueError, match="Lambda or anonymous functions are not supported"):
        @injected
        def wrapper():
            return lambda x: x + 1


def test_unnamed_functions_not_allowed():
    """Test that functions without __name__ attribute are not allowed."""
    from pinjected import injected, Injected

    # Create a function without __name__
    def make_unnamed():
        f = lambda x: x + 1
        delattr(f, "__name__")  # Force remove name
        return f

    # Test in Injected.bind
    with pytest.raises(ValueError, match="Cannot register a function without a proper name"):
        Injected.bind(make_unnamed())

    # Test in @injected decorator
    with pytest.raises(ValueError, match="Cannot register a function without a proper name"):
        @injected
        def wrapper():
            return make_unnamed()
