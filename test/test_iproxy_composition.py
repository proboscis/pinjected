import pytest
import pytest_asyncio
from pinjected import Injected, design
from pinjected.v2.async_resolver import AsyncResolver
from pinjected.di.expr_util import show_expr
from pinjected.v2.resolver import EvaluationError, SHOW_DETAILED_EVALUATION_CONTEXTS


class TestObject:
    """Test object with attributes and methods for IProxy testing."""
    
    def __init__(self, value):
        self.value = value
        self.items = {"a": 1, "b": 2, "c": 3}
    
    def multiply(self, factor):
        return self.value * factor
    
    def __str__(self):
        return f"TestObject({self.value})"


@pytest.mark.asyncio
async def test_iproxy_composition():
    """
    Test case for composing multiple IProxy objects with various operations
    (add, getitem, call, div, attribute access) and evaluating them with AsyncResolver.
    """
    num1 = Injected.pure(10).proxy
    num2 = Injected.pure(5).proxy
    test_obj = Injected.pure(TestObject(20)).proxy
    test_dict = Injected.pure({"x": 100, "y": 200, "z": 300}).proxy
    test_func = Injected.pure(lambda x: x * 2).proxy
    
    add_result = num1 + num2  # Should be 15
    
    div_result = num1 / num2  # Should be 2
    
    attr_access = test_obj.value  # Should be 20
    
    method_call = test_obj.multiply(3)  # Should be 60
    
    getitem_result = test_dict[Injected.pure("y").proxy]  # Should be 200
    
    func_call = test_func(num2)  # Should be 10
    
    complex_expr = (num1 + test_obj.value) / num2 + test_dict[Injected.pure("x").proxy]
    
    test_design = design(
        num1=num1,
        num2=num2,
        test_obj=test_obj,
        test_dict=test_dict,
        test_func=test_func,
        add_result=add_result,
        div_result=div_result,
        attr_access=attr_access,
        method_call=method_call,
        getitem_result=getitem_result,
        func_call=func_call,
        complex_expr=complex_expr
    )
    
    resolver = AsyncResolver(test_design)
    
    assert await resolver.provide("num1") == 10
    assert await resolver.provide("num2") == 5
    assert isinstance(await resolver.provide("test_obj"), TestObject)
    
    assert await resolver.provide("add_result") == 15
    assert await resolver.provide("div_result") == 2
    assert await resolver.provide("attr_access") == 20
    assert await resolver.provide("method_call") == 60
    assert await resolver.provide("getitem_result") == 200
    assert await resolver.provide("func_call") == 10
    assert await resolver.provide("complex_expr") == 106


@pytest.mark.asyncio
async def test_iproxy_exception_visualization():
    """
    Test case for visualizing exceptions in IProxy AST evaluation.
    Creates a proxy that always raises a RuntimeError and constructs a complex AST with it.
    Tests the enhanced exception traceback with detailed source error information.
    """
    import logging
    import sys
    import traceback
    from pinjected.di.expr_util import show_expr
    
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr,
                        format='%(asctime)s.%(msecs)03d | %(levelname)-8s | %(filename)s:%(funcName)s:%(lineno)d | %(message)s',
                        datefmt='%H:%M:%S')
    
    def error_func():
        raise RuntimeError("This is a test error in IProxy evaluation")
    
    error_proxy = Injected.bind(error_func).proxy
    
    num1 = Injected.pure(10).proxy
    test_obj = Injected.pure(TestObject(20)).proxy
    test_dict = Injected.pure({"x": 100, "y": 200, "z": 300}).proxy
    
    complex_error_expr1 = (num1 + error_proxy) / test_obj.value + test_dict[Injected.pure("x").proxy]
    complex_error_expr2 = test_obj.multiply(error_proxy) + num1
    complex_error_expr3 = test_dict[error_proxy]
    
    print("\nAST Structure for complex_error_expr1:")
    print(show_expr(complex_error_expr1))
    
    print("\nAST Structure for complex_error_expr2:")
    print(show_expr(complex_error_expr2))
    
    print("\nAST Structure for complex_error_expr3:")
    print(show_expr(complex_error_expr3))
    
    test_design = design(
        error_proxy=error_proxy,
        complex_error_expr1=complex_error_expr1,
        complex_error_expr2=complex_error_expr2,
        complex_error_expr3=complex_error_expr3
    )
    
    resolver = AsyncResolver(test_design)
    
    print("\nTesting simple error_proxy with detailed level information disabled:")
    with pytest.raises(Exception) as excinfo:
        await resolver.provide("error_proxy")
    print(f"\nException from error_proxy: {excinfo.value}")
    
    print("\nFull Exception Stack Trace with Source Error Details:")
    try:
        await resolver.provide("error_proxy")
    except Exception as e:
        print(traceback.format_exc())
        print(f"\nException type: {type(e)}")
        print(f"Exception attributes: {dir(e)}")
        
        assert isinstance(e, EvaluationError)
        assert hasattr(e, 'src')
        assert hasattr(e, 'eval_contexts')
        assert isinstance(e.src, RuntimeError)
        
        error_msg = str(e)
        assert "EvaluationError:" in error_msg
        assert "Context:" in error_msg, "Context section missing in default output"
        assert "Context Expr:" in error_msg, "Context Expr missing in default output"
        assert "Cause Expr:" in error_msg, "Cause Expr missing in default output"
        assert "Source Error:" in error_msg
        assert "Detailed Source Error Traceback:" in error_msg
        assert "RuntimeError: This is a test error in IProxy evaluation" in error_msg
        
        assert "Evaluation Path:" not in error_msg, "Evaluation Path should not be present in default output"
        assert "Context Details:" not in error_msg, "Context Details section should not be present in default output"
        assert "Level 0:" not in error_msg, "Level information should not be present in default output"
    
    print("\nTesting with detailed level information enabled:")
    try:
        global SHOW_DETAILED_EVALUATION_CONTEXTS
        global_flag_original = SHOW_DETAILED_EVALUATION_CONTEXTS
        SHOW_DETAILED_EVALUATION_CONTEXTS = True
        
        try:
            await resolver.provide("error_proxy")
        except EvaluationError as e:
            e.show_details = True
            print(f"\nManually set error.show_details to: {e.show_details}")
            raise e
    except Exception as e:
        print(f"\nException with detailed level information: {e}")
        
        if isinstance(e, EvaluationError):
            e.show_details = True
            error_msg = str(e)
        else:
            error_msg = str(e)
            
        print(f"\nGlobal flag value: {SHOW_DETAILED_EVALUATION_CONTEXTS}")
        print(f"\nError message with flag enabled:\n{error_msg}")
        
        assert "Context Details:" in error_msg, "Context Details section missing despite show_details=True"
        assert "Level 0:" in error_msg, "Level information missing despite show_details=True"
        assert "Context Expr:" in error_msg, "Context Expr missing despite show_details=True"
        assert "Cause Expr:" in error_msg, "Cause Expr missing despite show_details=True"
    finally:
        SHOW_DETAILED_EVALUATION_CONTEXTS = global_flag_original
    
    print("\nTesting complex_error_expr1:")
    with pytest.raises(Exception) as excinfo:
        await resolver.provide("complex_error_expr1")
    print(f"\nException from complex_error_expr1: {excinfo.value}")
    
    error_msg = str(excinfo.value)
    assert "Context:" in error_msg
    assert "Context Expr:" in error_msg
    assert "Cause Expr:" in error_msg
    assert "Source Error:" in error_msg
    assert "Detailed Source Error Traceback:" in error_msg
    
    print("\nTesting complex_error_expr2:")
    with pytest.raises(Exception) as excinfo:
        await resolver.provide("complex_error_expr2")
    print(f"\nException from complex_error_expr2: {excinfo.value}")
    
    print("\nTesting complex_error_expr3:")
    with pytest.raises(Exception) as excinfo:
        await resolver.provide("complex_error_expr3")
    print(f"\nException from complex_error_expr3: {excinfo.value}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_iproxy_composition())
