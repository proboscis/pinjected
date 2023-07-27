from pinject_design import Design, injected_function
from pinject_design.helpers import ModulePath

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


def test_to_script():
    from loguru import logger
    script = test_design.to_vis_graph().to_python_script(
        'test.test_visualization.c',
        "test.test_visualization.test_design"
    )
    logger.info(script)