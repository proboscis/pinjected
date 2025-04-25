from pinjected.compatibility.task_group import CompatibleExceptionGroup


def unwrap_exception_group(exc):
    while isinstance(exc, CompatibleExceptionGroup) and len(exc.exceptions) == 1:
        exc = exc.exceptions[0]
    return exc
