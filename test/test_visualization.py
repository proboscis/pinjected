from pinject_design import Design, injected_function

test_design=Design()
__default_design_paths__ = ['test.test_visualization.test_design']
@injected_function
def a():
    return "a"

@injected_function
def b(a,/):
    return a + "b"

@injected_function
def c(b,/):
    return b + "c"


