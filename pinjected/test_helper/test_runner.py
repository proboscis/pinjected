"""
Using PinjectedTestAggregator, We want to run the tests in organized manner...

1. run all test targets.
1.1 use subprocess
1.2 use pytest?

2. implement tagging for the runnables
2.1 gather all runnables or tests using tags.


"""
import asyncio
import io
import multiprocessing
import sys
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from returns.result import ResultE, Success, Failure
from pinjected import *
from pinjected.compatibility.task_group import TaskGroup
from pinjected.module_inspector import get_project_root, get_module_path
from pinjected.run_helpers.run_injected import run_injected, run_anything, a_run_target, a_run_target__mp
from pinjected.test_helper.test_aggregator import VariableInFile, PinjectedTestAggregator


@dataclass
class PinjectedTestResult:
    target: VariableInFile
    stdout: str
    stderr: str
    value: ResultE[Any]
    trace: Optional[str]

    def __str__(self):
        return f"PinjectedTestResult({self.target.to_module_var_path().path},{self.value})"

    def __repr__(self):
        return str(self)

    def failed(self):
        return isinstance(self.value, Failure)


@injected
async def a_pinjected_run_test(logger, /, target: VariableInFile) -> PinjectedTestResult:
    """
    1. get the ModuleVarPath from VariableInFile. but how?
    """
    mvp = target.to_module_var_path()
    # stdout = io.StringIO()
    # stderr = io.StringIO()
    # logger.add(stderr)
    # with redirect_stdout(stdout), redirect_stderr(stderr):
    # from loguru import logger
    stdout, stderr, trace, res = await a_run_target__mp(
        mvp.path,
    )
    if isinstance(res, Exception):
        res = Failure(res)
    else:
        res = Success(res)
    return PinjectedTestResult(
        target=target,
        stdout=stdout,
        stderr=stderr,
        value=res,
        trace=trace
    )


@instance
def pinjected_test_aggregator():
    return PinjectedTestAggregator()


@injected
async def a_pinjected_run_all_test(
        pinjected_test_aggregator: PinjectedTestAggregator,
        a_pinjected_run_test,
        logger,
        /,
        root: Path
):
    targets = pinjected_test_aggregator.gather(root)
    tasks = []
    async with TaskGroup() as tg:
        for target in targets:
            tasks.append(tg.create_task(a_pinjected_run_test(target)))
    for task in tasks:
        yield await task


@injected
def ensure_agen(items: list[VariableInFile] | AsyncIterator[VariableInFile]):
    if isinstance(items, list):
        async def gen():
            for t in items:
                yield t

        return gen()
    return items


@injected
async def a_run_tests(
        a_pinjected_run_test,
        ensure_agen,
        logger,
        /,
        tests: list[VariableInFile] | AsyncIterator[VariableInFile],
):
    # hmm, i want a queue here...
    from loguru import logger
    n_worker = multiprocessing.cpu_count()
    logger.info(f"n_worker={n_worker}")
    queue = asyncio.Queue()
    results = asyncio.Queue()

    async def enqueue():
        async for target in ensure_agen(tests):
            await queue.put(('task', target))
        for _ in range(n_worker):
            await queue.put(('stop', None))

    async def worker(idx):
        while True:
            task, target = await queue.get()
            if task == 'stop':
                await results.put(('stop', None))
                break
            res = await a_pinjected_run_test(target)
            await results.put(('result', res))

    async with TaskGroup() as tg:
        tg.create_task(enqueue())
        for i in range(n_worker):
            tg.create_task(worker(i))
        stop_count = 0
        while True:
            task, res = await results.get()
            if task == 'stop':
                stop_count += 1
                if stop_count == n_worker:
                    break
            else:
                yield res


@injected
async def a_visualize_test_results(
        logger,
        ensure_agen,
        /,
        tests: list[PinjectedTestResult] | AsyncIterator[PinjectedTestResult],
):
    results = []
    async for res in ensure_agen(tests):
        res: PinjectedTestResult
        if res.failed():
            logger.error(f"{res.target.to_module_var_path().path} -> {res.value}")
            print(f"============================= STDERR ===============================")
            print(res.stderr)
            logger.error(res.trace)
            print(f"====================================================================")
            pass
        else:
            logger.success(f"{res.target.to_module_var_path().path} -> {res.value}")
            pass
        results.append(res)
    failures = [r for r in results if r.failed()]
    # success = [r for r in results if not r.failed()]
    logger.info(f"Test finished with {len(failures)} / {len(results)} failures")
    return results


pinjected_run_tests_in_file: IProxy = a_visualize_test_results(
    a_run_tests(
        injected('pinjected_test_aggregator').gather_from_file(injected('pinjected_test_target_file')),
    )
)

with design(
        pinjected_test_target_file=Path(__file__).parent.parent.parent / "pinjected/test_package/child/module1.py",
):
    _run_test_in_file = pinjected_run_tests_in_file


@instance
async def __pinjected__internal_design():
    from pinjected.ide_supports.default_design import pinjected_internal_design
    return pinjected_internal_design


"""
Public interfaces:
"""


@injected
def test_current_file():
    pass


@injected
def test_tagged(*tags: str):
    pass


@injected
def test_tree():
    pass


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

__meta_design__ = design(
    overrides=__pinjected__internal_design
)
