"""Test file to verify @instance(callable=True) linter behavior."""

from pinjected import instance


# This should NOT trigger PINJ004 because it's marked callable=True
@instance(callable=True)
def callable_factory():
    def inner_func(x):
        return x * 2

    return inner_func


# This SHOULD trigger PINJ004 because it's a regular instance
@instance
def regular_factory():
    return {"data": "value"}


# Test direct calls
result = callable_factory()  # Should be OK - no PINJ004
value = result(5)  # Should be OK

data = regular_factory()  # Should trigger PINJ004
