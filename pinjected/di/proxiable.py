from abc import abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Any

T = TypeVar("T")


class IProxyContext(Generic[T]):

    @abstractmethod
    def getattr(self, tgt: T, name: str):
        pass

    @abstractmethod
    def call(self, tgt: T, *args, **kwargs):
        pass

    @abstractmethod
    def pure(self, tgt: T) -> "DelegatedVar[T]":
        pass

    @abstractmethod
    def getitem(self, tgt: T, key) -> Any:
        pass

    @abstractmethod
    def eval(self, tgt: T):
        pass

    @abstractmethod
    def alias_name(self):
        pass

    @abstractmethod
    def iter(self, tgt: T):
        pass

    @abstractmethod
    def dir(self, tgt):
        pass

    def biop_impl(self, op: str, tgt: T, other):
        """Bi-Operator Implementation
        op: '+' | '-' | '*' | '/' | '%' | '**' | '<<' | '>>' | '&' | '^' | '|' | '//'
        """
        raise NotImplementedError()

    def unary_impl(self, op: str, tgt: T):
        """Unary Operator Implementation
        op: '-' | '~' | 'len' | 'del'
        """
        raise NotImplementedError()


@dataclass
class DelegatedVar(Generic[T]):
    # Generic Var Type that delegates all implementations to cxt.
    __value__: T
    __cxt__: IProxyContext[T]

    def __getattr__(self, item):
        return self.__cxt__.getattr(self.__value__, item)

    def __call__(self, *args, **kwargs):
        res = self.__cxt__.call(self.__value__, *args, **kwargs)
        return res

    def __getitem__(self, key):
        return self.__cxt__.getitem(self.__value__, key)

    def eval(self) -> T:
        """this should return the semantic result of calculation."""
        return self.__cxt__.eval(self.__value__)

    def __str__(self):
        return f"{self.__cxt__.alias_name()}({self.__value__},{self.__cxt__})"

    def __iter__(self):
        return self.__cxt__.iter(self.__value__)

    def __getstate__(self):
        return self.__value__, self.__cxt__

    def __setstate__(self, state):
        self.__value__, self.__cxt__ = state

    def __hash__(self):
        return hash((self.__value__, self.__cxt__))

    def __add__(self, other):
        return self.__cxt__.biop_impl('+', self.__value__, other)

    def __mul__(self, other):
        return self.__cxt__.biop_impl('*', self.__value__, other)

    def __truediv__(self, other):
        return self.__cxt__.biop_impl('/', self.__value__, other)

    def __mod__(self, other):
        return self.__cxt__.biop_impl('%', self.__value__, other)

    def __eq__(self, other):
        return self.__cxt__.biop_impl('==', self.__value__, other)

    def __invert__(self):
        return self.__cxt__.unary_impl('~', self.__value__)

    def await__(self):
        return self.__cxt__.unary_impl('await', self.__value__)
