"""Test AST utility functions."""

import ast

from pinjected_linter.utils.ast_utils import (
    extract_function_defaults,
    find_all_names,
    find_await_calls,
    find_slash_position,
    get_call_names,
    get_decorator_names,
    get_function_params_after_slash,
    get_function_params_before_slash,
    get_string_value,
    has_decorator,
    is_design_call,
    is_function_call,
    is_iproxy_type_annotation,
    is_print_call,
)


def test_get_decorator_names_with_call():
    """Test getting decorator names from decorators with calls."""
    source = '''
@decorator1
@decorator2()
@decorator3(arg="value")
def my_function():
    pass
'''
    tree = ast.parse(source)
    func = tree.body[0]
    names = get_decorator_names(func)
    assert names == ["decorator1", "decorator2", "decorator3"]


def test_find_slash_position_with_posonlyargs():
    """Test finding slash position with position-only arguments."""
    source = '''
def func(a, b, /, c, d):
    pass
'''
    tree = ast.parse(source)
    func = tree.body[0]
    pos = find_slash_position(func.args)
    assert pos == 2  # Two position-only args


def test_find_slash_position_no_slash():
    """Test finding slash position when there's no slash."""
    source = '''
def func(a, b, c):
    pass
'''
    tree = ast.parse(source)
    func = tree.body[0]
    pos = find_slash_position(func.args)
    assert pos is None


def test_get_function_params_before_slash():
    """Test getting parameters before slash."""
    source = '''
def func(a, b, /, c, d):
    pass
'''
    tree = ast.parse(source)
    func = tree.body[0]
    params = get_function_params_before_slash(func)
    assert params == ["a", "b"]


def test_get_function_params_before_slash_no_slash():
    """Test getting parameters before slash when there's no slash."""
    source = '''
def func(a, b, c):
    pass
'''
    tree = ast.parse(source)
    func = tree.body[0]
    params = get_function_params_before_slash(func)
    assert params == []


def test_is_function_call_with_attribute():
    """Test is_function_call with attribute access."""
    source = '''
obj.method()
'''
    tree = ast.parse(source)
    call = tree.body[0].value
    assert is_function_call(call, "method") is True
    assert is_function_call(call, "other") is False


def test_find_all_names():
    """Test finding all names in an AST."""
    source = '''
a = b + c
d.method(e)
f = g[h]
'''
    tree = ast.parse(source)
    names = find_all_names(tree)
    assert names == {"b", "c", "d", "e", "g", "h"}


def test_get_call_names_with_attributes():
    """Test getting call names including method calls."""
    source = '''
func1()
obj.method()
module.func2()
'''
    tree = ast.parse(source)
    calls = get_call_names(tree)
    assert calls == {"func1", "method", "func2"}


def test_find_await_calls():
    """Test finding await expressions."""
    source = '''
async def func():
    x = await async_func1()
    y = await obj.async_method()
    return x + y
'''
    tree = ast.parse(source)
    awaits = find_await_calls(tree)
    assert len(awaits) == 2


def test_get_string_value_with_constant():
    """Test extracting string value from Constant node."""
    source = '''
"hello world"
'''
    tree = ast.parse(source)
    expr = tree.body[0].value
    value = get_string_value(expr)
    assert value == "hello world"


def test_get_string_value_non_string():
    """Test get_string_value with non-string node."""
    source = '''
42
'''
    tree = ast.parse(source)
    expr = tree.body[0].value
    value = get_string_value(expr)
    assert value is None


def test_is_design_call():
    """Test checking if a call is to design()."""
    source = '''
design(db=database)
'''
    tree = ast.parse(source)
    call = tree.body[0].value
    assert is_design_call(call) is True
    
    source2 = '''
other_func()
'''
    tree2 = ast.parse(source2)
    call2 = tree2.body[0].value
    assert is_design_call(call2) is False


def test_is_iproxy_type_annotation():
    """Test checking IProxy type annotations."""
    # Test simple IProxy
    ann = ast.Name(id="IProxy", ctx=ast.Load())
    assert is_iproxy_type_annotation(ann) is True
    
    # Test IProxy[Type]
    ann_subscript = ast.Subscript(
        value=ast.Name(id="IProxy", ctx=ast.Load()),
        slice=ast.Name(id="Database", ctx=ast.Load()),
        ctx=ast.Load()
    )
    assert is_iproxy_type_annotation(ann_subscript) is True
    
    # Test non-IProxy
    ann_other = ast.Name(id="OtherType", ctx=ast.Load())
    assert is_iproxy_type_annotation(ann_other) is False


def test_extract_function_defaults():
    """Test extracting function default values."""
    source = '''
def func(a, b=2, c=3, *, d=4, e, f=6):
    pass
'''
    tree = ast.parse(source)
    func = tree.body[0]
    defaults = extract_function_defaults(func)
    
    # Should have defaults for b, c, d, and f
    assert len(defaults) == 4
    param_names = [name for name, _ in defaults]
    assert param_names == ["b", "c", "d", "f"]


def test_is_print_call():
    """Test checking if a call is to print()."""
    source = '''
print("hello")
'''
    tree = ast.parse(source)
    call = tree.body[0].value
    assert is_print_call(call) is True
    
    source2 = '''
logger.info("hello")
'''
    tree2 = ast.parse(source2)
    call2 = tree2.body[0].value
    assert is_print_call(call2) is False