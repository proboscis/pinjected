import inspect
from typing import Callable, Tuple, Any, Dict
from loguru import logger


class MissingRequiredArgumentError(ValueError):
    pass


def fix_args_kwargs(func, args, kwargs):

    try:
        signature = inspect.signature(func)
    except ValueError:
        return args,kwargs
    bound_args = signature.bind(*args, **kwargs)
    bound_args.apply_defaults()
    # logger.info(f"func signature: {signature}")
    # logger.info(f"bound: {bound_args.arguments}")
    # logger.info(f"original: {args} {kwargs}")

    fixed_args = [bound_args.arguments[param.name] for param in signature.parameters.values() if
                  param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    var_positional_args = bound_args.arguments.get(
        next((param.name for param in signature.parameters.values() if param.kind == inspect.Parameter.VAR_POSITIONAL),
             None), ())
    fixed_kwargs = {param.name: bound_args.arguments[param.name] for param in signature.parameters.values() if
                    param.kind == inspect.Parameter.KEYWORD_ONLY}
    var_keyword_args = bound_args.arguments.get(
        next((param.name for param in signature.parameters.values() if param.kind == inspect.Parameter.VAR_KEYWORD),
             None), {})
    args = [*fixed_args, *var_positional_args]
    kwargs = fixed_kwargs | var_keyword_args
    logger.info(f"fixed: {args} {kwargs}")
    return args,kwargs

    #return tuple([*fixed_args, *var_positional_args]), fixed_kwargs | var_keyword_args
