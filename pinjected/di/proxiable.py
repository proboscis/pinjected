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
    value: T
    cxt: IProxyContext[T]

    def __getattr__(self, item):
        return self.cxt.getattr(self.value, item)

    def __call__(self, *args, **kwargs):
        res = self.cxt.call(self.value, *args, **kwargs)
        return res

    def __getitem__(self, key):
        return self.cxt.getitem(self.value, key)

    def eval(self) -> T:
        """this should return the semantic result of calculation."""
        return self.cxt.eval(self.value)

    def __str__(self):
        return f"{self.cxt.alias_name()}({self.value},{self.cxt})"

    def __iter__(self):
        return self.cxt.iter(self.value)

    def __getstate__(self):
        return self.value, self.cxt

    def __setstate__(self, state):
        self.value, self.cxt = state

    def __hash__(self):
        return hash((self.value, self.cxt))

    def __add__(self, other):
        return self.cxt.biop_impl('+', self.value, other)

    def __mul__(self, other):
        return self.cxt.biop_impl('*', self.value, other)

    def __truediv__(self, other):
        return self.cxt.biop_impl('/', self.value, other)

    def __mod__(self, other):
        return self.cxt.biop_impl('%', self.value, other)

    def __eq__(self, other):
        return self.cxt.biop_impl('==', self.value, other)

    def await__(self):
        return self.cxt.unary_impl('await', self.value)
