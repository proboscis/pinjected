from dataclasses import dataclass
from typing import Any, Dict

from pinjected.di.expr_util import Expr, Call
from pinjected.v2.keys import IBindKey
from pinjected.v2.provide_context import ProvideContext


@dataclass
class ResolverEvent:
    cxt: ProvideContext


@dataclass
class RequestEvent(ResolverEvent):
    key: IBindKey


@dataclass
class ProvideEvent(ResolverEvent):
    key: IBindKey
    data: Any


@dataclass
class DepsReadyEvent(ResolverEvent):
    key: IBindKey
    deps: Dict[IBindKey, Any]


@dataclass
class EvalRequestEvent(ResolverEvent):
    expr: Expr


@dataclass
class CallInEvalStart(ResolverEvent):
    expr: Call


@dataclass
class CallInEvalEnd(ResolverEvent):
    expr: Call
    result: Any


@dataclass
class EvalResultEvent(ResolverEvent):
    expr: Expr
    result: Any
