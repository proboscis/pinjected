from pinjected import injected


@injected
def my_function(dep1, /, arg1: str) -> str:
    return f"{dep1} {arg1}"


@injected
def another_function(dep2, /, arg2: int) -> int:
    return dep2 + arg2
