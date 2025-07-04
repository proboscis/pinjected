"""Test SymbolTable functionality."""

import ast

from pinjected_linter.utils.symbol_table import FunctionInfo, SymbolTable


def test_symbol_table_get_function():
    """Test getting function by name."""
    symbol_table = SymbolTable()
    
    # Add a function
    source = '''
@injected
def my_func(dep, /, arg):
    pass
'''
    tree = ast.parse(source)
    func_node = tree.body[0]
    symbol_table.add_function(func_node)
    
    # Test getting existing function
    func_info = symbol_table.get_function("my_func")
    assert func_info is not None
    assert func_info.name == "my_func"
    
    # Test getting non-existent function
    func_info = symbol_table.get_function("non_existent")
    assert func_info is None


def test_symbol_table_get_injected_functions():
    """Test getting all @injected functions."""
    symbol_table = SymbolTable()
    
    # Add various functions
    source = '''
@injected
def func1():
    pass

@instance
def func2():
    pass
    
@injected
def func3():
    pass
    
def func4():
    pass
'''
    tree = ast.parse(source)
    for node in tree.body:
        symbol_table.add_function(node)
    
    # Get injected functions
    injected = symbol_table.get_injected_functions()
    assert len(injected) == 2
    assert {f.name for f in injected} == {"func1", "func3"}


def test_symbol_table_get_instance_functions():
    """Test getting all @instance functions."""
    symbol_table = SymbolTable()
    
    # Add various functions
    source = '''
@injected
def func1():
    pass

@instance
def func2():
    pass
    
@instance
def func3():
    pass
    
def func4():
    pass
'''
    tree = ast.parse(source)
    for node in tree.body:
        symbol_table.add_function(node)
    
    # Get instance functions
    instances = symbol_table.get_instance_functions()
    assert len(instances) == 2
    assert {f.name for f in instances} == {"func2", "func3"}


def test_symbol_table_is_pinjected_function():
    """Test checking if a function has Pinjected decorators."""
    symbol_table = SymbolTable()
    
    # Add various functions
    source = '''
@injected
def func1():
    pass

@instance
def func2():
    pass
    
def func3():
    pass
'''
    tree = ast.parse(source)
    for node in tree.body:
        symbol_table.add_function(node)
    
    # Test pinjected functions
    assert symbol_table.is_pinjected_function("func1") is True
    assert symbol_table.is_pinjected_function("func2") is True
    assert symbol_table.is_pinjected_function("func3") is False
    assert symbol_table.is_pinjected_function("non_existent") is False


def test_symbol_table_extract_decorators_with_calls():
    """Test extracting decorators that are function calls."""
    symbol_table = SymbolTable()
    
    source = '''
@decorator1
@decorator2()
@decorator3(arg="value")
def my_func():
    pass
'''
    tree = ast.parse(source)
    func_node = tree.body[0]
    
    decorators = symbol_table._extract_decorators(func_node)
    assert decorators == ["decorator1", "decorator2", "decorator3"]


def test_symbol_table_get_injected_deps_before_slash():
    """Test getting dependencies before slash for @injected functions."""
    symbol_table = SymbolTable()
    
    # Add injected function with slash
    source = '''
@injected
def func1(dep1, dep2, /, arg1, arg2):
    pass
'''
    tree = ast.parse(source)
    func_node = tree.body[0]
    symbol_table.add_function(func_node)
    
    func_info = symbol_table.get_function("func1")
    deps = symbol_table.get_injected_deps_before_slash(func_info)
    assert deps == ["dep1", "dep2"]


def test_symbol_table_get_injected_deps_before_slash_no_slash():
    """Test getting dependencies when function has no slash."""
    symbol_table = SymbolTable()
    
    # Add injected function without slash
    source = '''
@injected
def func1(arg1, arg2):
    pass
'''
    tree = ast.parse(source)
    func_node = tree.body[0]
    symbol_table.add_function(func_node)
    
    func_info = symbol_table.get_function("func1")
    deps = symbol_table.get_injected_deps_before_slash(func_info)
    assert deps == []


def test_symbol_table_get_injected_deps_before_slash_not_injected():
    """Test getting dependencies for non-injected function."""
    symbol_table = SymbolTable()
    
    # Add non-injected function
    source = '''
@instance
def func1(dep1, dep2, /, arg1, arg2):
    pass
'''
    tree = ast.parse(source)
    func_node = tree.body[0]
    symbol_table.add_function(func_node)
    
    func_info = symbol_table.get_function("func1")
    deps = symbol_table.get_injected_deps_before_slash(func_info)
    assert deps == []