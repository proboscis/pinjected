from pinjected.pinjected_logging import logger
from pinjected.v2.callback import IResolverCallback
from pinjected.v2.events import (
    CallInEvalEnd,
    CallInEvalStart,
    DepsReadyEvent,
    EvalRequestEvent,
    EvalResultEvent,
    ProvideEvent,
    RequestEvent,
    ResolverEvent,
)

try:
    import nest_asyncio
    import importlib.util

    if importlib.util.find_spec("uvloop") is not None:
        logger.error(
            "nest_asyncio is disabled since uvloop is also installed! nest_asyncio.apply do not work with uvloop!"
        )
        nest_asyncio.apply = lambda: None
except ImportError:
    pass

import asyncio
import datetime
import operator
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Union

from pinjected.pinjected_logging import logger
from pinjected.di.expr_util import Cache, Call, Expr, UnaryOp, show_expr
from pinjected.v2.binds import IBind
from pinjected.v2.keys import IBindKey
from pinjected.v2.provide_context import ProvideContext

#
#
#
#
#
#   try:
#
PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS = (
    os.environ.get("PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS", "0") == "1"
)

Providable = Union[str, IBindKey, Callable, IBind]


class IScope(ABC):
    @abstractmethod
    def provide(
        self,
        tgt: IBindKey,
        cxt: ProvideContext,
        provider: Callable[[IBindKey, ProvideContext], Any],
    ):
        pass


@dataclass
class ScopeNode(IScope):
    objects: dict[IBindKey, Any] = field(default_factory=dict)

    def provide(
        self,
        tgt: IBindKey,
        cxt: ProvideContext,
        provider: Callable[[IBindKey, ProvideContext], Any],
    ):
        if tgt not in self.objects:
            self.objects[tgt] = provider(tgt, cxt)

        return self.objects[tgt]


# We need a lock for each Bind Key.


@dataclass
class AsyncLockMap:
    locks: dict[IBindKey, asyncio.Lock] = field(default_factory=dict)

    def get(self, key: IBindKey):
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        return self.locks[key]


OPERATORS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "//": operator.floordiv,
    "%": operator.mod,
    "**": operator.pow,
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "<<": operator.lshift,
    ">>": operator.rshift,
    "&": operator.and_,
    "|": operator.or_,
    "^": operator.xor,
}
UNARY_OPS = {
    "+": operator.pos,
    "-": operator.neg,
    "~": operator.invert,
    "not": operator.not_,
}


class EvaluationError(Exception):
    def __init__(
        self,
        cxt: ProvideContext,
        cxt_expr: Expr,
        cause_expr: Expr,
        src,
        parent_error=None,
    ):
        self.cxt = cxt
        self.cxt_expr = cxt_expr
        self.cause_expr = cause_expr
        self.src = src

        self.eval_contexts = []
        self.show_details = PINJECTED_SHOW_DETAILED_EVALUATION_CONTEXTS

        if parent_error and isinstance(parent_error, EvaluationError):
            self.eval_contexts.extend(parent_error.eval_contexts)
            self.show_details = parent_error.show_details

        self.eval_contexts.append(
            {
                "context": cxt.trace_str,
                "context_expr": show_expr(cxt_expr),
                "cause_expr": str(cause_expr),
            }
        )

        super().__init__("EvaluationError")

    def __str__(self):
        """
        Format the error message based on the current show_details flag value.
        This ensures the message reflects the flag's value at the time it's displayed.
        """
        error_msg = "EvaluationError:\n"

        if self.eval_contexts:
            if not self.show_details and self.eval_contexts:
                last_ctx = self.eval_contexts[-1]
                error_msg += f"Context: {last_ctx['context']}\n"
                error_msg += (
                    f"Context Expr: {self.truncate(last_ctx['context_expr'], 100)}\n"
                )
                error_msg += (
                    f"Cause Expr: {self.truncate(last_ctx['cause_expr'], 100)}\n"
                )
            else:
                error_msg += "Evaluation Path:\n"
                for i, ctx in enumerate(self.eval_contexts):
                    prefix = "  " * i
                    error_msg += f"{prefix}→ {self.truncate(ctx['context'], 80)}\n"

                if self.show_details:
                    error_msg += "\nContext Details:\n"
                    for i, ctx in enumerate(self.eval_contexts):
                        error_msg += f"  Level {i}:\n"
                        error_msg += f"    Context: {ctx['context']}\n"
                        error_msg += f"    Context Expr: {self.truncate(ctx['context_expr'], 100)}\n"
                        error_msg += (
                            f"    Cause Expr: {self.truncate(ctx['cause_expr'], 100)}\n"
                        )

        # error_msg += f"\nSource Error: {self.src}"

        # if isinstance(self.src, Exception):
        #     error_msg += self._format_source_exception(self.src)

        return error_msg

    def _format_source_exception(self, exc):
        """Format the source exception with detailed traceback information."""
        import traceback

        exc_type, exc_value, exc_tb = type(exc), exc, exc.__traceback__

        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)

        formatted_tb = "\n\nDetailed Source Error Traceback:\n"
        formatted_tb += "".join(tb_lines)

        return formatted_tb

    def truncate(self, text, n):
        if len(text) > n:
            return text[:n] + "..."
        return text


@dataclass
class ResolveStatus:
    key: Any
    kind: str  # eval or provide
    status: str
    start: datetime.datetime | None
    end: datetime.datetime | None


@dataclass
class BaseResolverCallback(IResolverCallback):
    def __post_init__(self):
        self.request_status: dict[IBindKey, str] = {}
        self.logger = logger.opt(colors=True, ansi=True)
        self.eval_status: dict[str, str] = {}
        self.total_status: dict[IBindKey | str] = {}

    def __call__(self, event: ResolverEvent):
        if isinstance(event, RequestEvent):
            self.on_request(event)
        elif isinstance(event, ProvideEvent):
            self.on_provide(event)
        elif isinstance(event, DepsReadyEvent):
            self.on_deps_ready(event)
        elif isinstance(event, EvalRequestEvent):
            self.on_eval_request(event)
        elif isinstance(event, EvalResultEvent):
            self.on_eval_result(event)
        elif isinstance(event, CallInEvalStart):
            self.on_call_in_eval_start(event)
        elif isinstance(event, CallInEvalEnd):
            self.on_call_in_eval_end(event)
        else:
            raise TypeError(f"event must be RequestEvent or ProvideEvent, got {event}")
        self.logger.info(f"{self.total_status_string()}")

    def provider_status_string(self):
        succeeded = [
            k for k in self.request_status if self.request_status[k] == "provided"
        ]
        running = [
            k for k in self.request_status if self.request_status[k] == "running"
        ]
        waiting = [
            k for k in self.request_status if self.request_status[k] == "waiting"
        ]
        succeeded = ", ".join([self._colored_key(k) for k in succeeded])
        running = ", ".join([self._colored_key(k) for k in running])
        waiting = ", ".join([self._colored_key(k) for k in waiting])
        res = f"Provided: [{succeeded}]\nWaiting: [{waiting}]\nRunning: [{running}]"
        return res

    def eval_status_string(self):
        awaiting = [k for k in self.eval_status if self.eval_status[k] == "await"]
        done = [k for k in self.eval_status if self.eval_status[k] == "done"]
        evaluating = [k for k in self.eval_status if self.eval_status[k] == "eval"]
        calling = [k for k in self.eval_status if self.eval_status[k] == "calling"]
        awaiting = ", ".join([self._colored_eval_key(k) for k in awaiting])
        done = ", ".join([self._colored_eval_key(k) for k in done])
        evaluating = ", ".join([self._colored_eval_key(k) for k in evaluating])
        calling = ", ".join([self._colored_eval_key(k) for k in calling])
        res = f"Awaiting:\t [{awaiting}]\nEvaluating:\t [{evaluating}]\nDone:\t\t [{done}]\nCalling:\t [{calling}]"
        return res

    def total_status_string(self):
        res = "\n===== RESOLVER STATUS =====\n"
        for k, v in self.state_string_dict().items():
            vals = list(v.values())
            res += f"{k}:\t"
            if vals:
                res += f"[{', '.join(vals[:10])}]\n"
            else:
                res += "[]\n"
            if len(v.values()) >= 10:
                res += f"and {len(vals) - 10} more...\n"
        return res

    def state_string_dict(self):
        provided = [
            k for k in self.request_status if self.request_status[k] == "provided"
        ]
        provided = {k: self._colored_key(k) for k in provided[:10]}
        running = [
            k for k in self.request_status if self.request_status[k] == "running"
        ]
        running = {k: self._colored_key(k) for k in running}
        waiting = [
            k for k in self.request_status if self.request_status[k] == "waiting"
        ]
        waiting = {k: self._colored_key(k) for k in waiting}

        eval_awaiting = [k for k in self.eval_status if self.eval_status[k] == "await"]
        eval_awaiting = {k: self._colored_eval_key(k) for k in eval_awaiting}
        eval_done = [k for k in self.eval_status if self.eval_status[k] == "done"]
        eval_done = {k: self._colored_eval_key(k) for k in eval_done}
        # eval_done = dict(TOTAL=f"{len(eval_done)} evaluations done.")

        eval_evaluating = [k for k in self.eval_status if self.eval_status[k] == "eval"]
        eval_evaluating = {k: self._colored_eval_key(k) for k in eval_evaluating}
        eval_calling = [k for k in self.eval_status if self.eval_status[k] == "calling"]
        eval_calling = {k: self._colored_eval_key(k) for k in eval_calling}
        return dict(
            Pending=waiting,
            Provided=provided,
            Running=running,
            Evaluating=eval_evaluating,
            Eval_Await=eval_awaiting,
            Eval_Call=eval_calling,
            Eval_Done=eval_done,
        )

    def _colored_eval_key(self, key: str):
        match self.eval_status[key]:
            case "await":
                return f"<yellow>{key}</yellow>"
            case "done":
                return f"<green>{key}</green>"
            case "eval":
                return f"<magenta>{key}</magenta>"
            case "calling":
                return f"<bold><yellow>{key}</yellow></bold>"

    def _colored_key(self, key: IBindKey):
        s = key.ide_hint_string()
        match self.request_status[key]:
            case "waiting":
                return f"<cyan>{s}</cyan>"
            case "running":
                return f"<yellow>{s}</yellow>"
            case "provided":
                return f"<green>{s}</green>"
            case _:
                raise ValueError(f"Unknown status {self.request_status[key]}")

    def on_request(self, event: RequestEvent):
        self.request_status[event.key] = "waiting"
        self.logger.info(f"{self.clean_msg(event.cxt.trace_str)}")
        self.total_status[event.key] = ResolveStatus(
            event.key, "provide", "waiting", datetime.datetime.now(), None
        )

    def on_provide(self, event: ProvideEvent):
        self.total_status[event.key].status = "provided"
        self.request_status[event.key] = "provided"
        data_str = str(event.data)[:50]
        data_str = self.clean_msg(data_str)
        self.logger.info(f"{self.clean_msg(event.cxt.trace_str)} := {data_str}")
        # self.logger.info(f"{self.provider_status_string()}")

    def on_deps_ready(self, event: DepsReadyEvent):
        self.total_status[event.key].status = "running"
        self.request_status[event.key] = "running"
        self.logger.info(f"{self.clean_msg(event.cxt.trace_str)}")
        # self.logger.info(f"{self.provider_status_string()}")

    def clean_msg(self, msg):
        return msg.replace("<", r"\<").replace(">", r"\>")

    def on_eval_request(self, event):
        expr = self.expr_repr(event.expr)
        match event.expr:
            case Cache(_):
                return
            case Call():
                self.total_status[expr] = ResolveStatus(
                    expr, "eval", "calling", datetime.datetime.now(), None
                )
                self.eval_status[expr] = "calling"
            case UnaryOp("await", _):
                self.total_status[expr] = ResolveStatus(
                    expr, "eval", "await", datetime.datetime.now(), None
                )
                self.eval_status[expr] = "await"
                # self.logger.debug(f"await\t -> <red>{expr}</red>")
            case _:
                self.total_status[expr] = ResolveStatus(
                    expr, "eval", "eval", datetime.datetime.now(), None
                )
                self.eval_status[expr] = "eval"
                # self.logger.debug(f"eval\t-> <magenta>{expr}</magenta>")
        # self.logger.info(f"\n{self.eval_status_string()}")

    def expr_repr(self, e):
        msg = show_expr(e)
        msg = self.clean_msg(msg)
        if len(msg) >= 50:
            msg = msg[:25] + "..." + msg[-25:]
        return msg

    def on_eval_result(self, event):
        expr = self.expr_repr(event.expr)
        res_msg = self.clean_msg(str(event.result)[:50])
        match event.expr:
            case Cache(_):
                return
            case Call():
                self.logger.success(f"call\t<- <magenta>{expr}</magenta>\t:= {res_msg}")
            case UnaryOp("await", _):
                self.logger.success(f"await <- <red>{expr}</red> := {res_msg}")
            case _:
                self.logger.debug(f"eval<- <magenta>{expr}</magenta> := {res_msg}")
        self.total_status[expr].status = "done"

        self.eval_status[expr] = "done"
        # self.logger.info(f"\n{self.eval_status_string()}")

    def on_call_in_eval_start(self, event: CallInEvalStart):
        expr_str = self.expr_repr(event.expr)
        self.logger.debug(f"call\t-> <magenta>{expr_str}</magenta>")

    def on_call_in_eval_end(self, event: CallInEvalEnd):
        expr_str = self.expr_repr(event.expr)
        self.logger.success(
            f"call\t<- <magenta>{expr_str}</magenta>\t:= {self.clean_msg(str(event.result)[:100])}"
        )
