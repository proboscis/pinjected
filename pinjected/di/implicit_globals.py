
from pinjected.v2.binds import IBind, BindInjected
from pinjected.v2.keys import IBindKey, StrBindKey
from pinjected.di.injected import Injected

IMPLICIT_BINDINGS: dict[IBindKey, IBind] = dict()

# Add loguru logger to implicit bindings
from pinjected.pinjected_logging import logger as pinjected_logger
from loguru import logger as loguru_logger

# Add logger to IMPLICIT_BINDINGS using lambda to follow the recommended pattern
IMPLICIT_BINDINGS[StrBindKey("logger")] = BindInjected(Injected.pure(lambda: loguru_logger))
