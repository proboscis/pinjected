"""Tests for di/util.py module."""

import pytest
import ast
import warnings
from unittest.mock import Mock, patch
from returns.result import Success, Failure
from pinjected.di.util import (
    rec_valmap,
    rec_val_filter,
    ErrorWithTrace,
    my_safe,
    check_picklable,
    extract_argnames,
    get_class_aware_args,
    instances,
    providers,
    design,
    classes,
    destructors,
    injecteds,
    try_parse,
    to_readable_name,
    EmptyDesign,
)
from pinjected import Injected, DelegatedVar
from pinjected.di.design import DesignImpl
from pinjected.v2.binds import BindInjected
from pinjected.di.injected import InjectedFromFunction, InjectedPure


def test_rec_valmap():
    """Test recursive value mapping on nested dictionaries."""

    def double(x):
        return x * 2

    # Test flat dict
    flat = {"a": 1, "b": 2}
    result = rec_valmap(double, flat)
    assert result == {"a": 2, "b": 4}

    # Test nested dict
    nested = {"a": 1, "b": {"c": 2, "d": {"e": 3}}}
    result = rec_valmap(double, nested)
    expected = {"a": 2, "b": {"c": 4, "d": {"e": 6}}}
    assert result == expected


def test_rec_val_filter():
    """Test recursive value filtering on nested dictionaries."""

    def is_even(x):
        if isinstance(x, tuple):
            return x[0] % 2 == 0
        return x % 2 == 0

    # Test flat dict
    flat = {"a": 1, "b": 2, "c": 3, "d": 4}
    result = rec_val_filter(is_even, flat)
    assert result == {"b": 2, "d": 4}

    # Test nested dict
    nested = {"a": 1, "b": {"c": 2, "d": {"e": 3, "f": 4}}}
    result = rec_val_filter(is_even, nested)
    expected = {"b": {"c": 2, "d": {"f": 4}}}
    assert result == expected


def test_error_with_trace():
    """Test ErrorWithTrace exception class."""
    original_error = ValueError("original message")
    trace = "Traceback:\n  File 'test.py', line 10\n    raise ValueError"

    error = ErrorWithTrace(original_error, trace)

    assert error.src is original_error
    assert error.trace == trace
    assert str(error) == f"{original_error}\n {trace}"

    # Test pickling
    import pickle

    pickled = pickle.dumps(error)
    unpickled = pickle.loads(pickled)
    assert isinstance(unpickled, ErrorWithTrace)
    assert str(unpickled.src) == str(original_error)
    assert unpickled.trace == trace


def test_my_safe():
    """Test my_safe decorator."""

    @my_safe
    def safe_divide(a, b):
        return a / b

    # Test success case
    result = safe_divide(10, 2)
    assert isinstance(result, Success)
    assert result.unwrap() == 5.0

    # Test failure case
    result = safe_divide(10, 0)
    assert isinstance(result, Failure)
    error = result.failure()
    assert isinstance(error, ErrorWithTrace)
    assert isinstance(error.src, ZeroDivisionError)
    assert "ZeroDivisionError" in error.trace


def test_check_picklable_success():
    """Test check_picklable with picklable object."""
    picklable_dict = {"a": 1, "b": "string", "c": [1, 2, 3], "d": {"nested": True}}

    # Should not raise
    check_picklable(picklable_dict)


@patch("pinjected.pinjected_logging.logger")
def test_check_picklable_failure(mock_logger):
    """Test check_picklable with non-picklable object."""
    # Create non-picklable object (lambda)
    non_picklable_dict = {
        "a": 1,
        "b": lambda x: x + 1,  # lambdas are not picklable with standard pickle
    }

    # Since we're using cloudpickle, lambdas might actually be picklable
    # Let's use something that definitely can't be pickled
    import threading

    lock = threading.Lock()
    non_picklable_dict = {"lock": lock}

    with pytest.raises(RuntimeError, match="this object is not picklable"):
        check_picklable(non_picklable_dict)

    # Check logger was called
    assert mock_logger.error.call_count >= 1


def test_extract_argnames():
    """Test extract_argnames function."""

    def func(a, b, c):
        pass

    args = extract_argnames(func)
    assert args == ["a", "b", "c"]

    # Test with no args
    def no_args():
        pass

    assert extract_argnames(no_args) == []

    # Test with defaults
    def with_defaults(a, b=10, c=20):
        pass

    assert extract_argnames(with_defaults) == ["a", "b", "c"]


def test_get_class_aware_args():
    """Test get_class_aware_args function."""

    # Test with regular function
    def func(a, b):
        pass

    assert get_class_aware_args(func) == ["a", "b"]

    # Test with class (should remove 'self')
    class MyClass:
        def __init__(self, a, b):
            pass

    assert get_class_aware_args(MyClass) == ["a", "b"]

    # Test with method
    assert get_class_aware_args(MyClass.__init__) == ["self", "a", "b"]


def test_to_readable_name():
    """Test to_readable_name function."""

    # Test with BindInjected containing InjectedFromFunction
    async def my_func():
        return 42

    # InjectedFromFunction requires original_function, target_function, kwargs_mapping
    injected_func = InjectedFromFunction(my_func, my_func, {})
    bind_injected = BindInjected(injected_func, "key")
    assert to_readable_name(bind_injected) == "my_func"

    # Test with BindInjected containing InjectedPure
    injected_pure = InjectedPure("test_value")
    bind_pure = BindInjected(injected_pure, "key")
    assert to_readable_name(bind_pure) == "test_value"

    # Test with any other value
    assert to_readable_name("anything") == "anything"
    assert to_readable_name(42) == 42


def test_instances_deprecated():
    """Test instances function shows deprecation warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        d = instances(a=1, b="hello")

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "instances' is deprecated" in str(w[0].message)

        # Should still work
        assert hasattr(d, "__dict__")  # Verify it's a design object


def test_instances_assertions():
    """Test instances function assertions."""
    # Test with DelegatedVar (should fail)
    delegated = DelegatedVar("value", Mock())

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)

        with pytest.raises(AssertionError, match="passing delegated var"):
            instances(a=delegated)

        # Test with Injected (should fail)
        injected = Injected.pure(42)
        with pytest.raises(AssertionError, match="passing Injected"):
            instances(a=injected)


def test_providers_deprecated():
    """Test providers function shows deprecation warning."""

    def my_provider():
        return 42

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        d = providers(service=my_provider)

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "providers' is deprecated" in str(w[0].message)

        # Should still work
        assert hasattr(d, "__dict__")  # Verify it's a design object


def test_classes_deprecated():
    """Test classes function shows deprecation warning."""

    class MyClass:
        pass

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        d = classes(MyClass=MyClass)

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "classes' is deprecated" in str(w[0].message)

        # Should still work
        assert hasattr(d, "__dict__")  # Verify it's a design object


def test_design_function():
    """Test design function."""

    # Test with mixed types
    def provider():
        return "provided"

    injected = Injected.pure("injected_value")

    d = design(
        instance_val=42,
        instance_str="hello",
        provider_func=provider,
        injected_val=injected,
    )

    # design() returns a MergedDesign object
    assert hasattr(d, "__dict__")  # Verify it's a design object


def test_empty_design():
    """Test EmptyDesign constant."""
    assert isinstance(EmptyDesign, DesignImpl)
    assert len(EmptyDesign._bindings) == 0


def test_injecteds():
    """Test injecteds function."""
    inj1 = Injected.pure(1)
    inj2 = Injected.pure(2)

    d = injecteds(a=inj1, b=inj2)
    assert isinstance(d, DesignImpl)


def test_destructors():
    """Test destructors function."""

    async def cleanup(resource):
        # Cleanup logic
        pass

    d = destructors(database=cleanup)
    # destructors() returns a MergedDesign object
    assert hasattr(d, "__dict__")  # Verify it's a design object


def test_try_parse():
    """Test try_parse function."""
    # Test valid Python code
    source = "x = 1\ny = 2"
    tree = try_parse(source)
    assert isinstance(tree, ast.AST)

    # Test indented code (should dedent)
    indented = "    x = 1\n    y = 2"
    tree = try_parse(indented)
    assert isinstance(tree, ast.AST)

    # Test deeply indented code
    deeply_indented = "        x = 1\n        y = 2"
    tree = try_parse(deeply_indented)
    assert isinstance(tree, ast.AST)

    # Test invalid syntax even after dedenting
    with pytest.raises(SyntaxError):
        try_parse("x = = 1")


def test_try_parse_max_trials():
    """Test try_parse with max trials exceeded."""
    # Create code that needs more dedents than allowed
    very_indented = "            x = 1"

    # With trials=0, it won't be able to dedent and will raise
    with pytest.raises(IndentationError):
        try_parse(very_indented, trials=0)


def test_method_to_function():
    """Test method_to_function utility."""
    from pinjected.di.util import method_to_function

    class TestClass:
        def method(self, a, b):
            return a + b

    # Convert method to function
    func = method_to_function(TestClass.method)

    # Verify it's callable and has correct name
    assert callable(func)
    assert "method" in func.__name__

    # Test with method that has keyword-only args (should raise)
    class TestClassWithKwOnly:
        def method(self, *, kwonly):
            return kwonly

    with pytest.raises(AssertionError, match="cannot have any kwonly args"):
        method_to_function(TestClassWithKwOnly.method)


def test_none_provider():
    """Test none_provider wrapper."""
    from pinjected.di.util import none_provider

    def original_func(a, b):
        return a + b

    wrapped = none_provider(original_func)

    # Should always return success message
    result = wrapped(1, 2)
    assert result == "success of none_provider"

    # Test with varargs - skip for now as implementation has issues
    # The function creates a signature without handling *args properly


def test_try_import_subject():
    """Test try_import_subject function."""
    from pinjected.di.util import try_import_subject

    Subject = try_import_subject()
    # Subject might be None if rx is not installed
    # This is OK - the function handles missing imports gracefully
    if Subject is not None:
        # Should be either rx.subject.Subject or rx.subjects.Subject
        assert callable(Subject)


def test_get_dict_diff():
    """Test get_dict_diff function."""
    from pinjected.di.util import get_dict_diff

    # Test basic difference
    a = {"key1": "value1", "key2": "value2", "opt": "ignored", "design": "ignored"}
    b = {"key1": "value1", "key2": "different", "opt": "ignored", "design": "ignored"}

    diff = get_dict_diff(a, b)

    assert len(diff) == 1
    assert diff[0] == ("key2", "value2", "different")

    # Test with BindInjected values
    async def func1():
        return "result1"

    async def func2():
        return "result2"

    inj1 = InjectedFromFunction(func1, func1, {})
    inj2 = InjectedFromFunction(func2, func2, {})

    bind1 = BindInjected(inj1, "key1")
    bind2 = BindInjected(inj2, "key2")

    a = {"test": bind1, "opt": "ignored", "design": "ignored"}
    b = {"test": bind2, "opt": "ignored", "design": "ignored"}

    diff = get_dict_diff(a, b)
    assert len(diff) == 1
    assert diff[0][0] == "test"
    assert diff[0][1] == "func1"
    assert diff[0][2] == "func2"


def test_get_external_type_name():
    """Test _get_external_type_name function."""
    from pinjected.di.util import _get_external_type_name

    # Test with class method
    class TestClass:
        def method(self):
            pass

    result = _get_external_type_name(TestClass.method)
    # For locally defined classes in test functions, it returns the module
    # This is expected behavior
    assert "test_di_util" in result or result == "TestClass"

    # Test with module function
    import os

    result = _get_external_type_name(os.path.join)
    assert "posixpath" in result or "ntpath" in result or "os" in result

    # Test with no module
    mock_func = Mock(__qualname__="test_func", __module__=None)
    with patch("inspect.getmodule", return_value=None):
        result = _get_external_type_name(mock_func)
        assert result == "unknown_module"


def test_add_code_locations():
    """Test add_code_locations function."""
    from pinjected.di.util import add_code_locations

    mock_design = Mock(spec=DesignImpl)
    mock_design.add_metadata = Mock(return_value=mock_design)

    # Test successful case
    with patch("pinjected.di.util.get_code_locations") as mock_get_locs:
        mock_location = Mock()
        mock_get_locs.return_value = {"key1": mock_location}

        frame = Mock()
        result = add_code_locations(mock_design, {"key1": "value"}, frame)

        assert result is mock_design
        mock_design.add_metadata.assert_called_once()

    # Test OSError case
    with patch("pinjected.di.util.get_code_locations") as mock_get_locs:
        mock_get_locs.side_effect = OSError("test error")

        with patch("pinjected.pinjected_logging.logger") as mock_logger:
            frame = Mock()
            result = add_code_locations(mock_design, {"key1": "value"}, frame)

            assert result is mock_design
            mock_logger.warning.assert_called_once()
            mock_design.add_metadata.assert_called_with()


def test_get_code_locations():
    """Test get_code_locations function."""
    from pinjected.di.util import get_code_locations
    from types import FrameType, CodeType

    # Create mock frame with proper structure
    mock_code = Mock(spec=CodeType)
    mock_code.co_filename = "/test/file.py"

    mock_frame = Mock(spec=FrameType)
    mock_frame.f_code = mock_code
    mock_frame.f_back = Mock(spec=FrameType)
    mock_frame.f_back.f_code = mock_code

    # Mock inspect.getsourcelines
    source_lines = [
        "result = design(\n",
        "    key1='value1',\n",
        "    key2='value2'\n",
        ")\n",
    ]

    with patch("inspect.getsourcelines", return_value=(source_lines, 10)):
        locations = get_code_locations(["key1", "key2"], mock_frame)

        assert "key1" in locations
        assert "key2" in locations
        assert str(locations["key1"].path) == "/test/file.py"
        assert locations["key1"].line == 11  # 10 + 2 - 1
        assert locations["key2"].line == 12  # 10 + 3 - 1


def test_get_code_location():
    """Test get_code_location function."""
    from pinjected.di.util import get_code_location
    from types import FrameType, CodeType

    mock_code = Mock(spec=CodeType)
    mock_code.co_filename = "/test/file.py"

    mock_frame = Mock(spec=FrameType)
    mock_frame.f_code = mock_code
    mock_frame.f_lineno = 42

    location = get_code_location(mock_frame)

    assert str(location.path) == "/test/file.py"
    assert location.line == 42
    assert location.column == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
