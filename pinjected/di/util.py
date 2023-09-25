import ast
import inspect
import textwrap
from pathlib import Path
from pprint import pformat
from types import FrameType
from typing import TypeVar, Dict, Union

import cloudpickle
from cytoolz import memoize
from makefun import create_function
from returns.maybe import Some
from returns.result import Failure, Success

from pinjected.di.design import Design
from pinjected.di.bindings import InjectedBind, BindMetadata
from pinjected.di.injected import Injected, InjectedPure, InjectedFunction
from pinjected.di.metadata.location_data import CodeLocation, ModuleVarLocation
from pinjected.di.monadic import getitem_opt
from pinjected.di.proxiable import DelegatedVar

# is it possible to create a binding class which also has an ability to dynamically add..?
# yes. actually.
T = TypeVar("T")


def rec_valmap(f, tgt: dict):
    res = dict()
    for k, v in tgt.items():
        if isinstance(v, dict):
            res[k] = rec_valmap(f, v)
        else:
            res[k] = f(v)
    return res


def rec_val_filter(f, tgt: dict):
    res = dict()
    for k, v in tgt.items():
        if isinstance(v, dict):
            res[k] = rec_val_filter(f, v)
        elif f(v):
            res[k] = v
    return res


class ErrorWithTrace(BaseException):
    def __init__(self, src: BaseException, trace: str):
        super().__init__()
        self.src = src
        self.trace = trace

    def __reduce__(self):
        return (ErrorWithTrace, (self.src, self.trace))

    def __str__(self):
        return f"{self.src}\n {self.trace}"


def my_safe(f):
    def impl(*args, **kwargs):
        try:
            return Success(f(*args, **kwargs))
        except Exception as e:
            import traceback
            trace = "\n".join(traceback.format_exception(e))

            return Failure(ErrorWithTrace(
                e,
                trace
            ))

    return impl


def check_picklable(tgt: dict):
    cloud_dumps_try = my_safe(cloudpickle.dumps)
    cloud_loads_try = my_safe(cloudpickle.loads)
    res = cloud_dumps_try(tgt).bind(cloud_loads_try)

    if isinstance(res, Failure):
        # target_check = valmap(cloud_dumps_try, tgt)
        rec_check = rec_valmap(lambda v: (cloud_dumps_try(v), v), tgt)
        failures = rec_val_filter(lambda v: isinstance(v[0], Failure), rec_check)
        # failures = [(k, v, tgt[k]) for k, v in target_check.items() if isinstance(v, Failure)]

        from loguru import logger
        logger.error(f"Failed to pickle target: {pformat(failures)}")
        logger.error(f"if the error message contains EncodedFile pickling error, "
                     f"check whether the logging module is included in the target object or not.")
        raise RuntimeError("this object is not picklable. check the error messages above.") from res.failure()
    # logger.info(res)


def method_to_function(method):
    """
    converts a class method to a function
    """
    argspec = inspect.getfullargspec(method)
    assert not isinstance(argspec.args, str)
    # assert not isinstance(argspec.varargs,str)
    signature = f"""f_of_{method.__name__}({" ,".join((argspec.args or []))})"""

    def impl(self, *args, **kwargs):
        return method(*args, **kwargs)  # gets multiple values for self

    assert len(argspec.kwonlyargs) == 0, "providing method cannot have any kwonly args"
    return create_function(signature, impl)


def none_provider(func):
    argspec = inspect.getfullargspec(func)
    signature = f"""none_provider({" ,".join((argspec.args or []) + (argspec.varargs or []))})"""

    def impl(*args, **kwargs):
        func(*args, **kwargs)  # gets multiple values for self
        return "success of none_provider"

    assert len(argspec.kwonlyargs) == 0, "providing method cannot have any kwonly args"
    return create_function(signature, impl)


def extract_argnames(func):
    spec = inspect.getfullargspec(func)
    return spec.args


def get_class_aware_args(f):
    args = inspect.getfullargspec(f).args
    if isinstance(f, type) and "self" in args:
        args.remove("self")
    return args


def to_readable_name(o):
    match o:
        case InjectedBind(InjectedFunction(func, _)):
            return func.__name__
        case InjectedBind(InjectedPure(value)):
            return value
        case any:
            return any


def try_import_subject():
    try:
        from rx.subject import Subject
        return Subject
    except Exception as e:
        from rx.subjects import Subject
        return Subject


def get_dict_diff(a: dict, b: dict):
    all_keys = list(sorted(set(a.keys()) | set(b.keys())))
    all_keys.remove("opt")
    # TODO check both contains transform design
    # all_keys.remove("base_train_transform_design")
    # all_keys.remove("base_test_transform_design")
    all_keys.remove("design")
    data = []
    Subject = try_import_subject()
    for k in all_keys:

        ak = getitem_opt(a, k).map(to_readable_name).value_or(None)
        bk = getitem_opt(b, k).map(to_readable_name).value_or(None)
        match (ak, bk):
            case (Subject(), Subject()):
                flag = True
            case (a, b):
                flag = a != b
            case _:
                raise RuntimeError("this should not happen")
        if flag:
            data.append((k, ak, bk))

    return data


T = TypeVar("T")

EmptyDesign = Design()


# mapping is another layer of complication.
# good way is to create a MappedDesign class which is not a subclass of a Design
# only MappedDesign or Design can be __add__ ed to this class
# calling to_design converts all lazy mapping into providers
# so if anything is missing then fails.

def _get_external_type_name(thing):
    """patch pinject's _get_external_type_name to accept pickled function"""
    qualifier = thing.__qualname__
    name = qualifier.rsplit('.', 1)[0]
    if hasattr(inspect.getmodule(thing), name):
        cls = getattr(inspect.getmodule(thing), name)
        if isinstance(cls, type):
            return cls.__name__

    res = inspect.getmodule(thing)  # .__name__
    if res is None:
        return "unknown_module"
    return res.__name__


def instances(**kwargs: Union[
    str, int, float, bool, dict, list, tuple, bytes, bytearray,object
]):
    for k, v in kwargs.items():
        assert not isinstance(v,
                              DelegatedVar), f"passing delegated var with Injected context is forbidden, to prevent human error."
        assert not isinstance(v,
                              Injected), f"key {k} is an instance of 'Injected'. passing Injected to 'instances' is forbidden, to prevent human error. use bind_instance instead."

    d = Design().bind_instance(**kwargs)
    return add_code_locations(d, kwargs, inspect.currentframe())


def providers(**kwargs):
    d = Design().bind_provider(**kwargs)
    # let's add the metadata for code_location here.
    # to do so, I need to get the source code of the parent frame
    # and then parse it to get the code_location.
    return add_code_locations(d, kwargs, inspect.currentframe())


def add_code_locations(design, kwargs, frame):
    locs = get_code_locations(list(kwargs.keys()), frame)
    metas = {k: BindMetadata(Some(loc)) for k, loc in locs.items()}
    return design.add_metadata(**metas)


@memoize
def try_parse(source: str, trials: int = 3) -> ast.AST:
    """
    Attempt to parse the source code, dedenting it if necessary.

    Args:
    - source (str): The source code to be parsed.
    - trials (int, optional): The maximum number of dedent trials. Defaults to 3.

    Returns:
    - ast.AST: The parsed AST of the source code.
    """
    try:
        return ast.parse(source)
    except IndentationError:
        if trials <= 0:
            raise  # re-raise the last IndentationError if max trials are exhausted
        return try_parse(textwrap.dedent(source), trials - 1)


def get_code_locations(keys: list[str], frame: FrameType) -> Dict[str, CodeLocation]:
    parent_frame = frame.f_back
    lines, start_line = inspect.getsourcelines(parent_frame)
    source = ''.join(lines)
    # logger.info(f"parsing:{source}")
    node = try_parse(source)

    locations = {}

    class ArgumentVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            node_lineno = node.lineno + start_line
            # parent_frame_lineno = parent_frame.f_lineno
            # print(f'node_match? {node_lineno} == {parent_frame_lineno} ?')
            # print(f"visit_Call:{node.lineno},{node.col_offset},{node},{start_line}, {parent_frame.f_lineno}")
            # print(f"node keywords:{node.keywords}")
            if node_lineno == parent_frame.f_lineno:  # The specific call that initiated the child frame
                for keyword in node.keywords:
                    if keyword.arg in keys:
                        locations[keyword.arg] = ModuleVarLocation(
                            Path(parent_frame.f_code.co_filename),
                            keyword.lineno + start_line,
                            keyword.col_offset + 1,
                        )

    ArgumentVisitor().visit(node)
    # print(locations)
    return locations


def get_code_location(frame):
    return ModuleVarLocation(
        Path(frame.f_code.co_filename),
        frame.f_lineno,
        0,
    )


def classes(**kwargs):
    d = Design().bind_class(**kwargs)
    return add_code_locations(d, kwargs, inspect.currentframe())


def injecteds(**kwargs):
    return Design().bind_provider(**kwargs)
