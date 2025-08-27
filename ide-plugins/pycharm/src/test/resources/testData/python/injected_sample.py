from pinjected import injected

@injected
def injected_function(dependency):
    return dependency.do_something()

# Injected variable
injected_var = injected(lambda: "injected value")

# Non-injected function
def regular_function():
    return "regular value"

# Non-injected variable
regular_var = "regular value"
