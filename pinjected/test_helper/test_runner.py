"""
Using PinjectedTestAggregator, We want to run the tests in organized manner...

1. run all test targets.
1.1 use subprocess
1.2 use pytest?

2. implement tagging for the runnables
2.1 gather all runnables or tests using tags.


"""

import asyncio
import multiprocessing
from abc import ABC
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, Callable

import rich
from returns.result import Failure, ResultE, Success
from rich.panel import Panel
from rich.spinner import Spinner

from pinjected import *
from pinjected.compatibility.task_group import TaskGroup
from loguru import logger as LoguruLogger
from pinjected.run_helpers.run_injected import a_run_target__mp
from pinjected.test_helper.rich_task_viz import RichTaskVisualizer, task_visualizer
from pinjected.test_helper.test_aggregator import (
    PinjectedTestAggregator,
    VariableInFile,
)


@dataclass
class PinjectedTestResult:
    target: VariableInFile
    stdout: str
    stderr: str
    value: ResultE[Any]
    trace: str | None

    def __str__(self):
        return (
            f"PinjectedTestResult({self.target.to_module_var_path().path},{self.value})"
        )

    def __repr__(self):
        return str(self)

    def failed(self):
        return isinstance(self.value, Failure)


def escape_loguru_tags(text):
    return text.replace("<", r"\<")


class CommandException(Exception):
    def __init__(self, message, code, stdout, stderr):
        super().__init__(message)
        self.message = message
        self.stdout = stdout
        self.stderr = stderr
        self.code = code

    def __reduce__(self):
        return self.__class__, (self.message, self.code, self.stdout, self.stderr)


# Forward declare Protocol classes - will be defined after ITestEvent
class APinjectedRunTestProtocol(Protocol):
    async def __call__(self, target: VariableInFile) -> PinjectedTestResult: ...


class APinjectedRunTestMultiprocessProtocol(Protocol):
    async def __call__(self, target: VariableInFile) -> PinjectedTestResult: ...


class APinjectedRunAllTestProtocol(Protocol):
    async def __call__(self, root: Path) -> AsyncIterator[PinjectedTestResult]: ...


class EnsureAgenProtocol(Protocol):
    def __call__(
        self, items: list[VariableInFile] | AsyncIterator[VariableInFile]
    ) -> AsyncIterator[VariableInFile]: ...


class ARunTestsProtocol(Protocol):
    async def __call__(
        self, tests: list[VariableInFile] | AsyncIterator[VariableInFile]
    ) -> AsyncIterator[PinjectedTestResult]: ...


class AVisualizeTestResultsProtocol(Protocol):
    async def __call__(
        self, tests: list[PinjectedTestResult] | AsyncIterator[PinjectedTestResult]
    ) -> Any: ...


class TestTaggedProtocol(Protocol):
    def __call__(self, *tags: str) -> Any: ...


@injected(protocol=APinjectedRunTestProtocol)
async def a_pinjected_run_test(
    logger: LoguruLogger,
    a_pinjected_test_event_callback: Callable[["ITestEvent"], Any],
    /,
    target: VariableInFile,
) -> PinjectedTestResult:
    import sys

    interpreter_path = sys.executable
    key = target.to_module_var_path().path
    command = f"{interpreter_path} -m pinjected run {target.to_module_var_path().path} --pinjected_no_notification"

    # prev_state = await a_get_stty_state()

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
        # WARNING! STDIN must be set, or the pseudo terminal will get reused and mess up the terminal
    )

    # Stream and capture stdout and stderr
    async def read_stream(tgt, kind: str):
        try:
            data = ""
            async for line in tgt:
                line = line.decode()
                data += line
                # logger.info(f"{kind}: {escape_loguru_tags(line)}")
                await a_pinjected_test_event_callback(EventInfo(key, StatusInfo(line)))
            return data
        except Exception as e:
            logger.error(f"read_stream failed with {e}")
            raise e

    await a_pinjected_test_event_callback(EventInfo(key, "start"))
    async with TaskGroup() as tg:
        # logger.info(f"waiting for command to finish: {command}")
        read_stdout_task = tg.create_task(read_stream(proc.stdout, "stdout"))
        read_stderr_task = tg.create_task(read_stream(proc.stderr, "stderr"))
        # logger.info(f"waiting for proc.wait()")
        result = await proc.wait()
        # logger.info(f"proc.wait() finished with {result}")
        stdout = await read_stdout_task
        # logger.info(f"stdout finished")
        stderr = await read_stderr_task
        # logger.info(f"stderr finished")
    # logger.info(f"command finished with:\n{stdout},{stderr}\nExitCode:{result}")
    if result == 0:
        # logger.success(f"command <<{command}>> finished with ExitCode:{result}")
        result = Success(result)
        trace = None
    else:
        import traceback

        # logger.error(f"command: <<{command}>> failed with code {result}.")
        trace = traceback.format_exc()
        exc = CommandException(
            f"command: <<{command}>> failed with code {result}.",
            # f"\nstdout: {stdout}"
            # f"\nstderr: {stderr}",
            code=result,
            stdout=stdout,
            stderr=stderr,
        )
        result = Failure(exc)
    res = PinjectedTestResult(
        target=target, stdout=stdout, stderr=stderr, value=result, trace=trace
    )
    await a_pinjected_test_event_callback(EventInfo(key, res))
    return res


@injected(protocol=APinjectedRunTestMultiprocessProtocol)
async def a_pinjected_run_test__multiprocess(
    logger: LoguruLogger, /, target: VariableInFile
) -> PinjectedTestResult:
    """
    1. get the ModuleVarPath from VariableInFile. but how?
    """
    mvp = target.to_module_var_path()
    # stdout = io.StringIO()
    # stderr = io.StringIO()
    # logger.add(stderr)
    # with redirect_stdout(stdout), redirect_stderr(stderr):
    # from pinjected.logging import logger
    # there is no way to capture the stdout/stderr using multiprocessing.Process
    # so we should instead use asyncio.create_subprocess_shell.
    stdout, stderr, trace, res = await a_run_target__mp(
        mvp.path,
    )
    if isinstance(res, Exception):
        res = Failure(res)
    else:
        res = Success(res)
    return PinjectedTestResult(
        target=target, stdout=stdout, stderr=stderr, value=res, trace=trace
    )


@instance
def pinjected_test_aggregator():
    return PinjectedTestAggregator()


@injected(protocol=APinjectedRunAllTestProtocol)
async def a_pinjected_run_all_test(
    pinjected_test_aggregator: PinjectedTestAggregator,
    a_pinjected_run_test: APinjectedRunTestProtocol,
    logger: LoguruLogger,
    /,
    root: Path,
):
    targets = pinjected_test_aggregator.gather(root)
    tasks = []
    async with TaskGroup() as tg:
        for target in targets:
            tasks.append(tg.create_task(a_pinjected_run_test(target)))
    for task in tasks:
        yield await task


@injected(protocol=EnsureAgenProtocol)
def ensure_agen(
    items: list[VariableInFile] | AsyncIterator[VariableInFile],
) -> AsyncIterator[VariableInFile]:
    if isinstance(items, list):

        async def gen():
            for t in items:
                yield t

        return gen()
    return items


class ITestEvent(ABC):
    pass


# Protocol that depends on ITestEvent
class APinjectedTestEventCallbackSimpleProtocol(Protocol):
    async def __call__(self, e: ITestEvent) -> None: ...


@dataclass
class MainTestEvent(ITestEvent):
    kind: Literal["start", "end"]


@dataclass
class StatusInfo:
    message: str


@dataclass
class EventInfo(ITestEvent):
    name: str
    data: Literal["queued", "start"] | PinjectedTestResult | StatusInfo


@injected(protocol=APinjectedTestEventCallbackSimpleProtocol)
async def a_pinjected_test_event_callback__simple(
    logger: LoguruLogger, /, e: ITestEvent
) -> None:
    # logger.info(f"EventInfo: {e}")
    match e:
        case EventInfo(_, PinjectedTestResult() as res):
            import rich
            from rich.panel import Panel

            if res.failed():
                tgt: VariableInFile = res.target
                mod_path = tgt.to_module_var_path().path
                mod_file = tgt.file_path
                msg = f'file\t:"{mod_file}"\ntarget\t:{tgt.name}\nstdout\t:{res.stdout}\nstderr\t:{res.stderr}'
                panel = Panel(msg, title=f"Failed ({mod_path})", style="bold red")
                rich.print(panel)
            else:
                rich.print(
                    Panel(
                        f"Success: {res.target.to_module_var_path().path}",
                        title="Success",
                        style="bold green",
                    )
                )
                # logger.success(f"{res.target.to_module_var_path().path} -> {res.value}")


@instance(callable=True)
async def a_pinjected_test_event_callback(
    logger,
):
    viz_fac = task_visualizer
    viz_iter = None
    viz: RichTaskVisualizer = None
    spinners = dict()
    active_tests = set()
    failures = []
    from rich.markup import escape

    def show_failure(res: PinjectedTestResult):
        tgt: VariableInFile = res.target
        mod_path = tgt.to_module_var_path().path
        mod_file = tgt.file_path
        msg = f'file\t:"{mod_file}"\ntarget\t:{tgt.name}\nstdout\t:{res.stdout}\nstderr\t:{res.stderr}'
        msg = escape(msg)
        panel = Panel(msg, title=f"Failed ({mod_path})", style="bold red")
        rich.print(panel)

    async def impl(e: ITestEvent):
        nonlocal viz, viz_iter, failures, active_tests
        # We must handle a case where TestMainEvent('start') is not called...
        # because the testfunction can be called solely.

        match e:
            # case MainTestEvent('start'):
            #     viz = await viz_iter.__aenter__()
            # case MainTestEvent('end'):
            #     await viz_iter.__aexit__(None, None, None)
            #     for res in failures:
            #         show_failure(res)
            # case EventInfo(_, 'queued'):
            #     viz.add(e.name, "queued", "")
            case EventInfo(key, "start"):
                if viz is None:
                    viz_iter = viz_fac()
                    viz = await viz_iter.__aenter__()
                active_tests.add(key)
                viz.add(e.name, "running", "")
                spinner = Spinner("aesthetic")
                spinners[e.name] = spinner
                viz.update_status(e.name, spinner)
            case EventInfo(_, StatusInfo(msg)):
                viz.update_message(e.name, escape(msg))
            case EventInfo(key, PinjectedTestResult() as res):
                active_tests.remove(key)
                if res.failed():
                    viz.update_status(e.name, "[bold red]Failed[/bold red]")
                    lines = res.stderr.split("\n")
                    viz.update_message(e.name, f"{lines[-3:]}")
                    failures.append(res)
                else:
                    viz.update_status(e.name, "[bold green]Success[/bold green]")
                    viz.update_message(e.name, "done")

                if not active_tests:
                    await viz_iter.__aexit__(None, None, None)
                    for res in failures:
                        show_failure(res)
                    viz = None

    return impl


@injected(protocol=ARunTestsProtocol)
async def a_run_tests(
    a_pinjected_run_test: APinjectedRunTestProtocol,
    ensure_agen: EnsureAgenProtocol,
    a_pinjected_test_event_callback: Callable[["ITestEvent"], Any],
    /,
    tests: list[VariableInFile] | AsyncIterator[VariableInFile],
) -> AsyncIterator[PinjectedTestResult]:
    # hmm, i want a queue here...
    from pinjected.pinjected_logging import logger

    n_worker = multiprocessing.cpu_count()
    logger.info(f"n_worker={n_worker}")
    queue = asyncio.Queue()
    results = asyncio.Queue()

    await a_pinjected_test_event_callback(MainTestEvent("start"))
    async with TaskGroup() as tg:

        async def enqueue():
            async for target in ensure_agen(tests):
                fut = asyncio.Future()
                key = target.to_module_var_path().path
                await queue.put(("task", target, fut))
                await a_pinjected_test_event_callback(EventInfo(key, "queued"))

            for _ in range(n_worker):
                await queue.put(("stop", target, None))

        async def worker(idx):
            while True:
                task, target, fut = await queue.get()
                if task == "stop":
                    await results.put(("stop", None))
                    break
                target.to_module_var_path().path
                res = await a_pinjected_run_test(target)
                fut.set_result(res)
                await results.put(("result", res))

        enqueue_task = tg.create_task(enqueue())
        worker_tasks = []
        for i in range(n_worker):
            worker_tasks.append(tg.create_task(worker(i)))
        stop_count = 0
        while True:
            task, res = await results.get()
            if task == "stop":
                stop_count += 1
                if stop_count == n_worker:
                    break
            else:
                yield res

        await enqueue_task
        for wt in worker_tasks:
            await wt
    await a_pinjected_test_event_callback(MainTestEvent("end"))


@injected(protocol=AVisualizeTestResultsProtocol)
async def a_visualize_test_results(
    logger: LoguruLogger,
    ensure_agen: EnsureAgenProtocol,
    /,
    tests: list[PinjectedTestResult] | AsyncIterator[PinjectedTestResult],
) -> None:
    results = []
    async for res in ensure_agen(tests):
        res: PinjectedTestResult
        # Nasty something breaks the stdout, and rich ends up corrupted.

        results.append(res)
    failures = [r for r in results if r.failed()]
    # success = [r for r in results if not r.failed()]
    logger.info(f"Test finished with {len(failures)} / {len(results)} failures")
    return results


pinjected_run_tests_in_file: IProxy = a_visualize_test_results(
    a_run_tests(
        injected("pinjected_test_aggregator").gather_from_file(
            injected("pinjected_test_target_file")
        ),
    )
)

with design(
    pinjected_test_target_file=Path(__file__).parent.parent.parent
    / "pinjected/test_package/child/module1.py",
):
    _run_test_in_file = pinjected_run_tests_in_file


@instance
async def __pinjected__internal_design():
    from pinjected.ide_supports.default_design import pinjected_internal_design

    return pinjected_internal_design


"""
Public interfaces:
"""


# This is not a test for pytest, but a user interface
def test_current_file():
    import inspect

    frame = inspect.currentframe().f_back
    file = frame.f_globals["__file__"]
    return a_visualize_test_results(
        a_run_tests(
            injected("pinjected_test_aggregator").gather_from_file(Path(file)),
        )
    )


@injected(protocol=TestTaggedProtocol)
def test_tagged(*tags: str) -> None:
    raise NotImplementedError


# This is not a test for pytet, but a user interface
def test_tree():
    import inspect

    frame = inspect.currentframe().f_back
    file = frame.f_globals["__file__"]

    return a_visualize_test_results(
        a_run_tests(
            injected("pinjected_test_aggregator").gather(Path(file)),
        )
    )


"""
So, pytest is like an interface to run bunch of small entrypoints.
For me, I can generalize this to running bunch of entrypoints with tags.
So, I want to tag many entrypoints and run them easily from the IDE by either clicking or via action.

Alright, now I've come to feel that I want to be able to add actions to the IDE via __meta_design__.
How can i add an entrypoint to run many tests?

1. Add a runnable variable that runs it..
2. This looks OK actually, right? I mean this looks better actually... and works on remote too :)
3. The problem would be the session... like, wandb.init() should be called only once.
Well, then use subprocess?

run_all_tests = pintest.test_this_file()
run_gpu_tests = pintest.test_tagged()
run_all_child_tests = pintest.test_children()

    
"""

# __meta_design__ = design(overrides=__pinjected__internal_design)
