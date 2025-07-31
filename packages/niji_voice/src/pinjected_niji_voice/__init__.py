# Python 3.13+ compatibility: ensure audioop is available for pydub
import sys

if sys.version_info >= (3, 13):
    try:
        import audioop  # noqa: F401
    except ImportError:
        try:
            import audioop_lts

            sys.modules["audioop"] = audioop_lts
        except ImportError:
            pass

from pinjected import design, instance


@instance
def loguru_logger():
    from loguru import logger

    return logger


__design__ = design(logger=loguru_logger)
