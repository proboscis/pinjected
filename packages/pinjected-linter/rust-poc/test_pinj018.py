from pinjected import injected


@injected
def my_function():
    pass


# This should trigger PINJ018
result = injected(my_function).proxy()
