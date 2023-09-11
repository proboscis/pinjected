INSPECT_TEMPLATE = f"""
There is a function annotatation called 'injected' that converts a function into a wrapped function.
Example:
@injected
def foo(dep1,dep2,/,x:int) -> int:
    return 1

foo: InjectedProxy[int -> int]
foo_call_result: Injected[int] = foo(1)

Injected is a monad that represents a value which requires dependency injection.
In the example above, the positional only arguments are considered as dependencies and get injected by the framework.
As a result, the function ends up with a single argument x:int and returns an int.
In the example above, the foo function is wrapped by InjectedProxy, which acts as a proxy for the call or attribute access inside the Injected monad. 
"""
