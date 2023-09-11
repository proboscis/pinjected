from pinjected import Design, injected_function, Injected
from pinjected.module_var_path import ModuleVarPath

test_design=Design()
__default_design_paths__ = ['test.test_visualization.test_design']
@injected_function
def a():
    return "a"

@injected_function
def b(a,/):
    return a() + "b"

@injected_function
def c(b,/):
    return b() + "c"

d:Injected = c() + "d"

