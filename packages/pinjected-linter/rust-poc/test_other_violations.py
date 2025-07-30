"""Test other known violations"""

from pinjected import injected


# PINJ009 violation - direct call to injected function
@injected
def my_func():
    pass


my_func()  # This should trigger PINJ009
