import sys
def _init_loguru_logger():
    from loguru import logger as loguru_logger
    default_format= (
        "<green>{time:HH:mm:ss.SSS} | "
        "<level>{level: <8}</level> | "
        "<cyan>{file.name}:{function}</cyan>:<cyan>{line}</cyan> |</green> "
    )
    tagged_format= (
        "<green>{time:HH:mm:ss.SSS} | "
        "<level>{level: <8}</level> | "
        "<magenta>[{extra[tag]}]</magenta> | "
        "<cyan>{file.name}:{function}</cyan>:<cyan>{line}</cyan> |</green> "
    )
    logger = loguru_logger#.bind(tag="pinjected")
    loguru_logger.remove()
    loguru_logger.add(
        sys.stderr,
        filter = lambda r: 'tag' not in r['extra'],
        format = default_format + "<level>{message}</level>",
        colorize=True
    )
    loguru_logger.add(
        sys.stderr,
        filter = lambda r: 'tag' in r['extra'],
        format = tagged_format + "<level>{message}</level>",
        colorize=True
    )
    return logger

def _init_logger():
    from logging import getLogger
    logger = getLogger("pinjected")
    return logger


logger = _init_loguru_logger()
