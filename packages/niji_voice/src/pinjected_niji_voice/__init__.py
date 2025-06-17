from pinjected import design, instance


@instance
def loguru_logger():
    from loguru import logger

    return logger


__design__ = design(logger=loguru_logger)
