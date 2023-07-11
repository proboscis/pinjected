import abc
import asyncio
import functools
import hashlib
import inspect
import sys
from copy import copy
from dataclasses import dataclass, field
from typing import List, Generic, Union, Callable, TypeVar, Tuple, Set, Dict

from makefun import create_function

from pinject_design.di.implicit_globals import IMPLICIT_BINDINGS
from pinject_design.di.injected_analysis import get_instance_origin
from pinject_design.di.proxiable import DelegatedVar
from loguru import logger

T, U = TypeVar("T"), TypeVar("U")

A = TypeVar("A")
B = TypeVar("B")


@dataclass
class FrameInfo:
    filename: str
    line_number: int
    function_name: str
    sources: List[str]
    line_idx_in_sources: int


def get_frame_info(stack_idx) -> Union[None, FrameInfo]:
    try:
        return FrameInfo(*inspect.getframeinfo(inspect.stack(0)[stack_idx][0]))
    except Exception as e:
        return None


def partialclass(name, cls, *args, **kwds):
    """
    copied from https://stackoverflow.com/questions/38911146/python-equivalent-of-functools-partial-for-a-class-constructor
    :param name:
    :param cls:
    :param args:
    :param kwds:
    :return:
    """
    new_cls = type(name, (cls,), {
        '__init__': functools.partialmethod(cls.__init__, *args, **kwds)
    })

    # The following is copied nearly ad verbatim from `namedtuple's` source.
    """
    # For pickling to work, the __module__ variable needs to be set to the frame
    # where the named tuple is created.  Bypass this step in enviroments where
    # sys._getframe is not defined (Jython for example) or sys._getframe is not
    # defined for arguments greater than 0 (IronPython).
    """
    try:
        new_cls.__module__ = sys._getframe(1).f_globals.get('__name__', '__main__')
    except (AttributeError, ValueError):
        pass

    return new_cls


@dataclass
class ParamInfo:
    params_to_fill: Dict  # = tgt_sig.parameters
    params_state: Dict  # = dict()
    vargs: List = field(default_factory=list)  # = []
    kwargs: Dict = field(default_factory=dict)  # = dict()
    # the problem is we may or may not have vargs and kwargs...


class Injected(Generic[T], metaclass=abc.ABCMeta):
    """
    this class is actually an abstraction of fucntion partial application.
    TODO I need a way to store dynamic dependencies
    """

    @staticmethod
    def partial(original_function: Callable, **injection_targets: "Injected") -> "Injected[Callable]":
        """
        use this to partially inject specified params, and leave the other parameters to be provided after injection is resolved.
        This implementation is very ugly.
        :param original_function: Callable
        :param injection_targets: specific parameters to make injected automatically
        :return: Injected[Callable[(params which were not specified in injection_targets)=>Any]]
        """
        # TODO WARNING DO NOT EVER USE LOGGER HERE. IT WILL CAUSE PICKLING ERROR on ray's nested remote call!
        original_sig = inspect.signature(original_function)

        # USING a logger in here make things very difficult to debug. because makefun doesnt seem to keep __closure__
        # hmm we need to check if the args are positional only or not.
        # in that case we need to inject with *args.
        def _get_new_signature(funcname, missing_params):
            missing_non_defaults = [p for p in missing_params if
                                    p.default is inspect.Parameter.empty and p.kind != inspect.Parameter.VAR_KEYWORD and p.kind != inspect.Parameter.VAR_POSITIONAL]
            # hmm, we need to check if the original_funcion is a method or not.
            # if method, ignore the first param.

            vkwarg = [p for p in missing_params if p.kind == inspect.Parameter.VAR_KEYWORD]
            if not vkwarg:
                vkwarg = [inspect.Parameter('__kwargs', inspect.Parameter.VAR_KEYWORD)]
            varg = [p for p in missing_params if p.kind == inspect.Parameter.VAR_POSITIONAL]
            if not varg:
                varg = [inspect.Parameter('__args', inspect.Parameter.VAR_POSITIONAL)]
            # we also need to pass varargs if there are default args..
            new_func_sig = f"_injected_partial_{funcname}({','.join([str(p).split(':')[0] for p in (missing_non_defaults + varg + vkwarg)])})"
            return new_func_sig

        def makefun_impl(injected_kwargs):
            # this gets called every time you call this function through PartialInjectedFunction interface
            # this is because the injected_kwargs gets changed.

            missing_keys = [k for k in original_sig.parameters.keys() if k not in injected_kwargs]
            missing_params = [original_sig.parameters[k] for k in missing_keys]
            missing_positional_args = [p for p in missing_params if p.kind == inspect.Parameter.POSITIONAL_ONLY]
            missing_non_positional_args = [p for p in missing_params if
                                           p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD]
            new_func_sig = _get_new_signature(original_function.__name__, missing_params)
            defaults = {p.name: p.default for p in missing_params if p.default is not inspect.Parameter.empty}

            def func_gets_called_after_injection_impl(*_args, **_kwargs):
                assert len(_args) >= len(
                    missing_positional_args), f"not enough args for positional only args:{missing_positional_args}"
                num_missing_positional_args = len(missing_positional_args)
                inferred_pos_arg_names = [p.name for p in missing_positional_args]
                inferred_non_pos_arg_names = [p.name for p in missing_non_positional_args]
                inferred_positional_args, inferred_non_positional_args = _args[:num_missing_positional_args], _args[
                                                                                                              num_missing_positional_args:]
                # logger.info(f"inferred positional args:{inferred_positional_args}")
                # logger.info(f"inferred non positional args:{inferred_non_positional_args}")
                # logger.info(f"inferred positional arg names:{inferred_pos_arg_names}")
                # logger.info(f"inferred non positional arg names:{inferred_non_pos_arg_names}")
                total_kwargs = copy(defaults)
                filled_kwargs = {**injected_kwargs,
                                 **dict(zip(inferred_pos_arg_names, inferred_positional_args)),
                                 **dict(zip(inferred_non_pos_arg_names, inferred_non_positional_args)),
                                 **_kwargs}
                # logger.info(f"filled kwargs:{filled_kwargs}")
                total_kwargs.update(filled_kwargs)
                # logger.info(f"total kwargs:{total_kwargs}")
                args = [total_kwargs[k] for k, p in original_sig.parameters.items() if
                        p.kind != inspect.Parameter.VAR_KEYWORD and p.kind != inspect.Parameter.VAR_POSITIONAL and p.kind != inspect.Parameter.KEYWORD_ONLY]
                # we need to put the ramaining args into kwargs if kwargs is present in the signature
                vks = [p for k, p in original_sig.parameters.items() if p.kind == inspect.Parameter.VAR_KEYWORD]
                if vks:
                    kwargs = {k: v for k, v in total_kwargs.items() if k not in original_sig.parameters.keys()}
                else:
                    kwargs = {}
                # we also need to handle kwonly args
                kws = [p for k, p in original_sig.parameters.items() if p.kind == inspect.Parameter.KEYWORD_ONLY]
                if kws:
                    for k in kws:
                        kwargs[k.name] = total_kwargs[k.name]
                vas = [p for k, p in original_sig.parameters.items() if p.kind == inspect.Parameter.VAR_POSITIONAL]
                if vas:
                    # we need to put the ramaining args into kwargs if kwargs is present in the signature
                    vargs = _args[num_missing_positional_args + len(missing_non_positional_args):]
                else:
                    vargs = []
                # hmm we need to pass kwargs too..
                # logger.info(f"args:{args}")
                # args contains values from kwargs...
                # logger.info(f"vargs:{vargs}")
                # logger.info(f"kwargs:{kwargs}")
                bind_result = original_sig.bind(*args, *vargs, **kwargs)
                bind_result.apply_defaults()
                # logger.info(f"bound args:{bind_result.args}")
                # logger.info(f"bound kwargs:{bind_result.kwargs}")
                # Ah, since the target_function is async, we can't catch...
                return original_function(*bind_result.args, **bind_result.kwargs)

            from loguru import logger
            # logger.info(f"injected.partial -> {new_func_sig} ")
            new_func = create_function(
                new_func_sig,
                func_gets_called_after_injection_impl,
                doc=original_function.__doc__,
            )
            __doc__ = original_function.__doc__
            __skeleton__ = f"""def {new_func_sig}:
    \"\"\"
    {__doc__}
    \"\"\"
"""
            new_func.__skeleton__ = __skeleton__

            return new_func

        makefun_impl.__name__ = original_function.__name__
        if isinstance(original_function, type):
            makefun_impl.__original_code__ = "not available"
            makefun_impl.__original_file__ = "not available"
        elif type(original_function).__name__ == 'staticmethod':
            makefun_impl.__original_code__ = inspect.getsource(original_function.__func__)
            makefun_impl.__original_file__ = inspect.getfile(original_function.__func__)
        else:
            makefun_impl.__original_code__ = inspect.getsource(original_function)
            # staticmethod is not allowed?
            makefun_impl.__original_file__ = inspect.getfile(original_function)
        makefun_impl.__doc__ = original_function.__doc__
        injected_kwargs = Injected.dict(**injection_targets)
        # hmm?
        # Ah, so upon calling instance.method(), we need to manually check if __self__ is present?
        injected_factory = PartialInjectedFunction(
            Injected.bind(makefun_impl, injected_kwargs=injected_kwargs)
        )
        # the inner will be called upon calling the injection result.
        # This involves many internal Injecte instances. can I make it simler?
        # it takes *by_name, mzip, and map.
        injected_factory.__runnable_metadata__ = {
            "kind": "callable"
        }

        return injected_factory

    @staticmethod
    def inject_except(target_function, *whitelist: str) -> "Injected[Callable]":
        """
        :param target_function:
        :param whitelist: name of arguments which should not be injected by DI.
        :return: Injected[Callable[(whitelisted args)=>Any]]
        """
        argspec = inspect.getfullargspec(target_function)
        args_to_be_injected = [a for a in argspec.args if a not in whitelist and a != "self"]
        return Injected.partial(target_function, **{item: Injected.by_name(item) for item in args_to_be_injected})

    @staticmethod
    def bind(_target_function_, **kwargs_mapping: Union[str, type, Callable, "Injected"]) -> "InjectedFunction":
        if isinstance(_target_function_, Injected):
            _target_function_ = _target_function_.get_provider()
        return InjectedFunction(
            target_function=_target_function_,
            kwargs_mapping=kwargs_mapping
        )

    @staticmethod
    def direct(_target_function, **kwargs) -> "Injected":
        """
        uses Injected.pure by default unless the parameter is an instance of Injected.
        :param _target_function:
        :param kwargs:
        :return:
        """
        en_injected = {k: Injected.pure(v) for k, v in kwargs.items() if not isinstance(v, (Injected, DelegatedVar))}
        already_injected = {k: v for k, v in kwargs.items() if isinstance(v, (Injected, DelegatedVar))}
        return Injected.bind(_target_function, **en_injected, **already_injected)

    def _faster_get_fname(self):
        try:
            frame = sys._getframe().f_back.f_back.f_back.f_back
            mod = frame.f_globals["__name__"]
            name = frame.f_lineno
            return f"{mod.replace('.', '_')}_L_{name}".replace("<", "__").replace(">", "__")
        except Exception as e:
            # from loguru import logger
            # logger.warning(f"failed to get name of the injected location.")
            return f"__unknown_module__maybe_due_to_pickling__"

    def __init__(self):
        self.fname = self._faster_get_fname()

    def apply_partial(self, *args: "Injected", **kwargs: "Injected"):
        assert all(isinstance(a, Injected) for a in args), f"{args} is not all Injected"
        assert all(isinstance(a, Injected) for a in kwargs.values()), f"{kwargs} is not all Injected"
        args = Injected.mzip(*args)
        kwargs = Injected.dict(**kwargs)
        f = self
        res = Injected.mzip(f, args, kwargs).map(
            lambda f_args_kwargs: functools.partial(f_args_kwargs[0], *f_args_kwargs[1], **f_args_kwargs[2]))
        return PartialInjectedFunction(res)

    @abc.abstractmethod
    def dependencies(self) -> Set[str]:
        pass

    def dynamic_dependencies(self) -> Set[str]:
        """
        :return: a set of dependencies which are not statically known. mainly used for analysis.
        use this to express an injected that conditionally depends on something, such as caches.
        """
        return self.dependencies()

    def get_signature(self):
        sig = f"""{self.fname}({",".join(self.dependencies())})"""
        # logger.warning(sig)
        return sig

    @abc.abstractmethod
    def get_provider(self):
        """
        :return: a provider
        """

    def map(self, f: Callable[[T], U]) -> 'Injected[U]':
        return MappedInjected(self, f)

    def from_impl(impl: Callable, dependencies: Set[str]):
        return GeneratedInjected(impl, dependencies)

    @staticmethod
    def pure(value):
        return InjectedPure(value)

    @staticmethod
    def by_name(name: str):
        return InjectedByName(name, )

    def zip(self, other: "Injected[U]") -> "Injected[Tuple[T,U]]":
        assert isinstance(self, Injected)
        assert isinstance(other, Injected)
        return ZippedInjected(self, other)

    @staticmethod
    def mzip(*srcs: "Injected"):
        srcs = [Injected.ensure_injected(s) for s in srcs]
        return MZippedInjected(*srcs)

    @staticmethod
    def list(*srcs: "Injected"):
        return Injected.mzip(*srcs).map(list)

    @staticmethod
    def map_elements(f: "Injected[Callable]", elements: "Injected[Iterable]") -> "Injected[Iterable]":
        """
        for (
            f <- f,
            elements <- elements
            ) yield map(f,elements)
        :param f:
        :param elements:
        :return:
        """
        return Injected.mzip(
            f, elements
        ).map(lambda x: map(x[0], x[1]))

    # this is ap of applicative functor.
    def apply_injected_function(self, other: "Injected[Callable[[T],U]]") -> "Injected[U]":
        return self.zip(other).map(
            lambda t: t[1](t[0])
        )

    def and_then_injected(self, other: "Injected[Callable[[T],U]]") -> "Injected[Callable[[Any],U]]":
        return self.zip(other).map(
            lambda t: lambda *args, **kwargs: t[1](t[0](*args, **kwargs))
        )

    @staticmethod
    def dict(**kwargs: "Injected") -> "Injected[Dict]":
        keys = list(kwargs.keys())
        return Injected.mzip(*[kwargs[k] for k in keys]).map(lambda t: {k: v for k, v in zip(keys, t)})

    @property
    def proxy(self) -> DelegatedVar:
        """use this to modify injected variables freely without map.
        call eval() at the end to finish modification
        # it seems this thing is preventing from pickling?
        """
        from pinject_design.di.app_injected import injected_proxy
        return injected_proxy(self)

    @staticmethod
    def ensure_injected(data: Union["Injected", DelegatedVar]):
        match data:
            case DelegatedVar():
                return Injected.ensure_injected(data.eval())
            case Injected():
                return data
            case func if callable(func):
                return Injected.bind(func)
            case _:
                raise RuntimeError(f"not an injected object: {data},type(data)={type(data)}")

    def __add__(self, other: "Injected"):
        match other:
            case int() | float() | str():
                other = Injected.pure(other)
        other = Injected.ensure_injected(other)
        return self.zip(other).map(lambda t: t[0] + t[1])

    def desync(self):
        return self.map(lambda coroutine: asyncio.run(coroutine))

    def __len__(self):
        return self.map(len)

    # Implementing these might end up with pickling issues. due to recursive getattr..?
    # def __call__(self, *args, **kwargs):
    #     return self.proxy(*args, **kwargs)
    #
    # def __getitem__(self, item):
    #     return self.proxy[item]


@dataclass
class ConditionalInjected(Injected):
    condition: Injected[bool]
    true: Injected
    false: Injected

    def dependencies(self) -> Set[str]:
        return self.condition.dependencies()

    def get_provider(self):
        def task(session: "IObjectGraph", condition: bool):
            if condition:
                return session[self.true]
            else:
                return session[self.false]

        return Injected.bind(task, condition=self.condition).get_provider()

    def dynamic_dependencies(self) -> Set[str]:
        return self.condition.dynamic_dependencies() | \
            self.true.dynamic_dependencies() | \
            self.false.dynamic_dependencies()


@dataclass
class InjectedCache(Injected[T]):
    cache: Injected[Dict]
    program: Injected[T]
    program_dependencies: List[Injected]

    def __post_init__(self):
        def impl(session, cache: Dict, *deps):
            logger.info(f"Checking for cache with deps:{deps}")
            sha256_key = hashlib.sha256(str(deps).encode()).hexdigest()
            hash_key = sha256_key
            if hash_key not in cache:
                logger.info(f"Cache miss for {deps}")
                data = session[self.program]
                cache[hash_key] = data
            else:
                logger.info(f"Cache hit for {deps},loading ...")
            res = cache[hash_key]
            logger.info(f"Cache hit for {deps}, loaded")
            return res

        self.impl = Injected.list(
            Injected.by_name("session"),
            self.cache,
            *self.program_dependencies
        ).map(
            lambda t: impl(*t)
        )

    def get_provider(self):
        return self.impl.get_provider()

    def dependencies(self) -> Set[str]:
        return self.impl.dependencies()

    def dynamic_dependencies(self) -> Set[str]:
        return self.impl.dynamic_dependencies() | \
            self.program.dynamic_dependencies()

    def __hash__(self):
        return hash(self.impl)


class GeneratedInjected(Injected):
    """creates Injected from dependencies and funct(**kwargs) signature"""

    def __init__(self, impl: Callable, dependencies: Set[str]):
        super().__init__()
        self.impl = impl
        self._dependencies = dependencies

    def dependencies(self) -> Set[str]:
        return self._dependencies

    def get_provider(self):
        return create_function(self.get_signature(), func_impl=self.impl)


class MappedInjected(Injected):
    __match_args__ = ("src", "f")

    def __init__(self, src: Injected[T], f: Callable[[T], U]):
        super(MappedInjected, self).__init__()
        self.src = src
        self.f: Callable[[T], U] = f

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        def impl(**kwargs):
            assert self.dependencies() == set(
                kwargs.keys())  # this is fine but get_provider returns wrong signatured func
            tmp = self.src.get_provider()(**kwargs)
            return self.f(tmp)

        return create_function(self.get_signature(), func_impl=impl)


def extract_dependency_including_self(f: Union[type, Callable]):
    if isinstance(f, type):  # it's a constructor and we must use __init__ for backward compatibility.
        argspec = inspect.getfullargspec(f.__init__)
        return set(argspec.args)
    elif isinstance(f, Callable):
        argspec = inspect.getfullargspec(f)
        return set(argspec.args)
    else:
        raise RuntimeError(f"input:{f} is not either type or Callable")


def extract_dependency(dep: Union[str, type, Callable, Injected, DelegatedVar[Injected]]) -> Set[str]:
    if isinstance(dep, str):
        return {dep}
    elif isinstance(dep, type):  # it's a constructor and we must use __init__ for backward compatibility.
        argspec = inspect.getfullargspec(dep.__init__)
        return set(argspec.args) - {'self'}
    elif isinstance(dep, DelegatedVar):
        return extract_dependency(dep.eval())
    elif isinstance(dep, Injected):
        return dep.dependencies()
    elif isinstance(dep, Callable):
        try:
            argspec = inspect.getfullargspec(dep)
        except Exception as e:
            from loguru import logger
            logger.error(f"failed to get argspec of {dep}. of type {type(dep)}")
            raise e

        return set(argspec.args) - {'self'}
    else:
        raise RuntimeError(f"dep must be either str/type/Callable/Injected. got {type(dep)}")


def solve_injection(dep: Union[str, type, Callable, Injected], kwargs: dict):
    if isinstance(dep, str):
        return kwargs[dep]
    elif isinstance(dep, DelegatedVar):
        return solve_injection(dep.eval(), kwargs)
    elif isinstance(dep, Injected):
        return solve_injection(dep.get_provider(), kwargs)
    elif isinstance(dep, (type, Callable)):
        return dep(**{k: kwargs[k] for k in extract_dependency(dep)})
    else:
        raise RuntimeError(f"dep must be one of str/type/Callable/Injected. got {type(dep)}")


def combine_image_store(a, b):
    # do anything
    return a + b


def assert_kwargs_type(v):
    if isinstance(v, str):
        return
    if isinstance(v, type):
        return
    if isinstance(v, Callable):
        return
    if isinstance(v, Injected):
        return
    else:
        raise TypeError(f"{type(v)} is not any of [str,type,Callable,Injected]")


class InjectedFunction(Injected[T]):
    # since the behavior differs in classes extending Generic[T]
    __match_args__ = ("target_function", "kwargs_mapping")

    def __init__(self,
                 target_function: Callable,
                 kwargs_mapping: Dict[str, Union[str, type, Callable, Injected, DelegatedVar]]
                 ):
        # I think we need to know where this class is instantiated outside of pinject_design_package
        self.origin_frame = get_instance_origin("pinject_design")
        super().__init__()
        assert not isinstance(target_function, (Injected, DelegatedVar))
        assert callable(target_function)
        self.target_function = target_function
        self.kwargs_mapping = copy(kwargs_mapping)
        for k, v in self.kwargs_mapping.items():
            assert v is not None, f"injected got None binding for key:{k}"
            assert_kwargs_type(v)
            if isinstance(v, DelegatedVar):
                self.kwargs_mapping[k] = v.eval()
        # logger.info(f"InjectedFunction:{self.target_function} kwargs_mapping:{self.kwargs_mapping}")
        org_deps = extract_dependency(self.target_function)
        # logger.info(f"tgt:{target_function} original dependency:{org_deps}")
        missings = {d for d in org_deps if d not in self.kwargs_mapping}
        # logger.info(f"now missing {missings}")
        # logger.warning(f"created InjectedFunction:{inspect.signature(target_function)}")
        # assert "self" not in inspect.signature(target_function).parameters
        self.missings = missings

    def override_mapping(self, **kwargs: Union[str, type, Callable, Injected]):
        return InjectedFunction(self.target_function, {**self.kwargs_mapping, **kwargs})

    def get_provider(self):
        signature = self.get_signature()

        def impl(**kwargs):
            deps = dict()
            for mdep in self.missings:
                deps[mdep] = solve_injection(mdep, kwargs)
            for k, dep in self.kwargs_mapping.items():
                deps[k] = solve_injection(dep, kwargs)
            # logger.info(f"calling function:{self.target_function.__name__}{inspect.signature(self.target_function)}")
            # logger.info(f"src mapping:{self.kwargs_mapping}")
            # logger.info(f"with deps:{deps}")
            return self.target_function(**deps)

        # you have to add a prefix 'provider'""
        return create_function(func_signature=signature, func_impl=impl)

    def dependencies(self) -> Set[str]:
        # ahhhh this recursively demands for injection.
        # we need to distinguish what and what not to recursively inject
        res = set()
        for mdep in self.missings:
            d = extract_dependency(mdep)
            res |= d
            # logger.info(f"deps of missing:{d}")
        for k, dep in self.kwargs_mapping.items():
            d = extract_dependency(dep)
            res |= d
            # logger.info(f"deps of dependency({k}):{d}")
        return res

    # def __str__(self):
    #    return f"""InjectedFunction(target={self.target_function},kwargs_mapping={self.kwargs_mapping})"""


class InjectedPure(Injected[T]):
    __match_args__ = ("value",)

    def __init__(self, value):
        super().__init__()
        self.value = value

    def dependencies(self) -> Set[str]:
        return set()

    def get_provider(self):
        return create_function(func_signature=self.get_signature(), func_impl=lambda: self.value)

    def __str__(self):
        return f"Pure({self.value})"

    def __repr__(self):
        return str(self)


class InjectedByName(Injected[T]):
    __match_args__ = ("name",)

    def __init__(self, name):
        super().__init__()
        self.name = name

    def dependencies(self) -> Set[str]:
        return {self.name}

    def get_provider(self):
        return create_function(func_signature=self.get_signature(), func_impl=lambda **kwargs: kwargs[self.name])

    def __str__(self):
        return f"InjectedByName({self.name})"

    def __repr__(self):
        return str(self)


class ZippedInjected(Injected[Tuple[A, B]]):
    __match_args__ = ("a", "b")

    def __init__(self, a: Injected[A], b: Injected[B]):
        super().__init__()
        assert isinstance(a, Injected), f"got {type(a)} for a"
        assert isinstance(b, Injected), f"got {type(b)} for b"
        self.a = a
        self.b = b

    def dependencies(self) -> Set[str]:
        return set(self.a.dependencies() | self.b.dependencies())

    def get_provider(self):
        def impl(**kwargs):  # can we pickle this though?
            a_kwargs = {k: kwargs[k] for k in self.a.dependencies()}
            b_kwargs = {k: kwargs[k] for k in self.b.dependencies()}
            a = self.a.get_provider()(**a_kwargs)
            b = self.b.get_provider()(**b_kwargs)
            return a, b

        signature = self.get_signature()
        # logger.info(f"created signature:{signature} for ZippedInjected")
        return create_function(func_signature=signature, func_impl=impl)


class MZippedInjected(Injected):
    __match_args__ = ("srcs",)

    def __init__(self, *srcs: Injected):
        super().__init__()
        self.srcs = [Injected.ensure_injected(item) for item in srcs]
        assert all(isinstance(s, Injected) for s in self.srcs), self.srcs

    def dependencies(self) -> Set[str]:
        res = set()
        for s in self.srcs:
            res |= s.dependencies()
        return res

    def get_provider(self):
        def impl(**kwargs):  # can we pickle this though?
            each_kwargs = [{k: kwargs[k] for k in s.dependencies()} for s in self.srcs]
            res = []
            for s in self.srcs:
                r = s.get_provider()(**{k: kwargs[k] for k in s.dependencies()})
                res.append(r)
            return tuple(res)

        signature = self.get_signature()
        # from loguru import logger
        # logger.info(f"created signature:{signature} for MZippedInjected")
        return create_function(func_signature=signature, func_impl=impl)


def _injected_factory(**targets: Injected):
    def _impl(f):
        return Injected.partial(f, **targets)

    return _impl


class InjectedWithDefaultDesign(Injected):
    __match_args__ = ('src', 'default_design_path')

    def __init__(self, src: Injected, default_design_path: str):
        super().__init__()
        self.src = src  # why does this receive 4 play buttons?
        self.default_design_path: str = default_design_path

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        return self.src.get_provider()


def with_default(design_path: str):
    def _impl(f):
        return InjectedWithDefaultDesign(Injected.ensure_injected(f), design_path)

    return _impl


@dataclass
class RunnableInjected(Injected):
    src: Injected
    design_path: str
    working_dir: str

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        return self.src.get_provider()


@dataclass
class PartialInjectedFunction(Injected):
    src: Injected[Callable]

    def __post_init__(self):
        assert isinstance(self.src, Injected), f"src:{self.src} is not an Injected"

    def __call__(self, *args, **kwargs) -> DelegatedVar:
        return self.src.proxy(*args, **kwargs)

    def dependencies(self) -> Set[str]:
        return self.src.dependencies()

    def get_provider(self):
        # logger.warning(f"PartialInjectedFunction.get_provider() is called here.")
        return self.src.get_provider()

    def __hash__(self):
        return hash(self.src)


def injected_function(f) -> PartialInjectedFunction:
    """
    any args starting with "_" or positional_only kwargs is considered to be injected.
    :param f:
    :return:
    """
    # How can we make this work on a class method?
    sig: inspect.Signature = inspect.signature(f)
    tgts = dict()
    for k, v in sig.parameters.items():
        # does this contain self?
        # assert k != 'self', f"self is not allowed in injected_function... for now:{f}"
        #
        if k.startswith("_"):
            tgts[k] = Injected.by_name(k[1:])
        elif v.kind == inspect.Parameter.POSITIONAL_ONLY:
            tgts[k] = Injected.by_name(k)
    new_f = Injected.partial(f, **tgts)

    IMPLICIT_BINDINGS[f.__name__] = new_f

    return new_f


def injected_instance(f) -> Injected:
    sig: inspect.Signature = inspect.signature(f)
    tgts = {k: Injected.by_name(k) for k, v in sig.parameters.items()}
    instance = Injected.partial(f, **tgts)().eval()
    IMPLICIT_BINDINGS[f.__name__] = instance
    return instance


def injected_method(f):
    _impl = injected_function(f)

    def impl(self, *args, **kwargs):
        return _impl(self, *args, **kwargs)

    return impl


def injected_class(cls):
    return injected_function(cls)


def injected(name: str):
    return Injected.by_name(name).proxy
