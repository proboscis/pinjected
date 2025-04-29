from pinjected import design, injected
from pinjected.schema.handlers import (
    PinjectedHandleMainException,
    PinjectedHandleMainResult,
)

with design(x=10):
    y = injected("x")
    with design(y=20):
        z = injected("y")
    with design(x=100):
        z2 = y

default_design = design()


@injected
async def __handle_exception(e: Exception):
    print(f"Exception: {e}")
    return "handled"


@injected
async def __handle_success(result):
    print(f"Success: {result}")


__test_handling_design = design(
    **{
        PinjectedHandleMainException.key.name: __handle_exception,
        PinjectedHandleMainResult.key.name: __handle_success,
    }
)


__design__ = design() + __test_handling_design
