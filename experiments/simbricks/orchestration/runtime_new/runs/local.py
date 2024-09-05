# Copyright 2021 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import annotations

import asyncio

from simbricks.orchestration import exectools
from simbricks.orchestration.runners import ExperimentSimpleRunner
from simbricks.orchestration.runtime.common import Run, Runtime

from simbricks.orchestration.runtime_new import simulation_executor
from simbricks.orchestration.runtime_new import command_executor
from simbricks.orchestration.runtime_new.runs import base as run_base


class LocalSimpleRuntime(run_base.Runtime):
    """Execute runs locally in sequence."""

    def __init__(
        self,
        verbose=False,
        executor: command_executor.Executor = command_executor.LocalExecutor(),
    ):
        super().__init__()
        self._runnable: list[run_base.Run] = []
        self._complete: list[run_base.Run] = []
        self._verbose: bool = verbose
        self._executor: command_executor.Executor = executor
        self._running: asyncio.Task | None = None

    def add_run(self, run: run_base.Run) -> None:
        self._runnable.append(run)

    async def do_run(self, run: run_base.Run) -> None:
        """Actually executes `run`."""
        try:
            runner = simulation_executor.ExperimentSimpleRunner(
                self._executor, run._simulation, run._inst_env, self.verbose
            )
            if self._profile_int:
                runner.profile_int = self.profile_int
            await run.prep_dirs(self.executor)
            await runner.prepare()
        except asyncio.CancelledError:
            # it is safe to just exit here because we are not running any
            # simulators yet
            return

        run.output = await runner.run()  # handles CancelledError
        self._complete.append(run)

        # if the log is huge, this step takes some time
        if self._verbose:
            print(f"Writing collected output of run {run.name()} to JSON file ...")

        output_path = run._instantiation.get_simulation_output_path(
            run_number=run._run_nr
        )
        run._output.dump(outpath=output_path)

    async def start(self) -> None:
        """Execute the runs defined in `self.runnable`."""
        for run in self.runnable:
            if self._interrupted:
                return

            self._running = asyncio.create_task(self.do_run(run))
            await self._running

    def interrupt_handler(self) -> None:
        if self._running:
            self._running.cancel()


class LocalParallelRuntime(run_base.Runtime):
    """Execute runs locally in parallel on multiple cores."""

    def __init__(
        self,
        cores: int,
        mem: int | None = None,
        verbose: bool = False,
        executor: command_executor.Executor = command_executor.LocalExecutor(),
    ):
        super().__init__()
        self._runs_noprereq: list[run_base.Run] = []
        """Runs with no prerequesite runs."""
        self._runs_prereq: list[run_base.Run] = []
        """Runs with prerequesite runs."""
        self._complete: set[run_base.Run] = set()
        self._cores: int = cores
        self._mem: int | None = mem
        self._verbose: bool = verbose
        self._executor = executor

        self._pending_jobs: set[asyncio.Task] = set()
        self._starter_task: asyncio.Task

    def add_run(self, run: run_base.Run) -> None:
        if run._simulation.resreq_cores() > self._cores:
            raise RuntimeError("Not enough cores available for run")

        if self._mem is not None and run._simulation.resreq_mem() > self._mem:
            raise RuntimeError("Not enough memory available for run")

        if run._prereq is None:
            self._runs_noprereq.append(run)
        else:
            self._runs_prereq.append(run)

    async def do_run(self, run: run_base.Run) -> run_base.Run | None:
        """Actually executes `run`."""
        try:
            runner = simulation_executor.ExperimentSimpleRunner(
                self._executor, run._simulation, run._inst_env, self._verbose
            )
            if self._profile_int is not None:
                runner._profile_int = self._profile_int
            await run.prep_dirs(executor=self._executor)
            await runner.prepare()
        except asyncio.CancelledError:
            # it is safe to just exit here because we are not running any
            # simulators yet
            return None

        print("starting run ", run.name())
        run._output = await runner.run()  # already handles CancelledError

        # if the log is huge, this step takes some time
        if self.verbose:
            print(f"Writing collected output of run {run.name()} to JSON file ...")

        output_path = run._instantiation.get_simulation_output_path(
            run_number=run._run_nr
        )
        run._output.dump(outpath=output_path)
        print("finished run ", run.name())
        return run

    async def wait_completion(self) -> None:
        """Wait for any run to terminate and return."""
        assert self._pending_jobs

        done, self._pending_jobs = await asyncio.wait(
            self._pending_jobs, return_when=asyncio.FIRST_COMPLETED
        )

        for r_awaitable in done:
            run = await r_awaitable
            self._complete.add(run)
            self._cores_used -= run._simulation.resreq_cores()
            self._mem_used -= run._simulation.resreq_mem()

    def enough_resources(self, run: run_base.Run) -> bool:
        """Check if enough cores and mem are available for the run."""
        simulation = run._simulation  # pylint: disable=redefined-outer-name

        if self._cores is not None:
            enough_cores = (self._cores - self._cores_used) >= simulation.resreq_cores()
        else:
            enough_cores = True

        if self._mem is not None:
            enough_mem = (self.mem - self.mem_used) >= simulation.resreq_mem()
        else:
            enough_mem = True

        return enough_cores and enough_mem

    def prereq_ready(self, run: run_base.Run) -> bool:
        """Check if the prerequesite run for `run` has completed."""
        if run._prereq is None:
            return True

        return run._prereq in self._complete

    async def do_start(self) -> None:
        """Asynchronously execute the runs defined in `self.runs_noprereq +
        self.runs_prereq."""
        # self.completions = asyncio.Queue()
        self._cores_used = 0
        self._mem_used = 0

        runs = self._runs_noprereq + self._runs_prereq
        for run in runs:
            # if necessary, wait for enough memory or cores
            while not self.enough_resources(run):
                print("waiting for resources")
                await self.wait_completion()

            # if necessary, wait for prerequesite runs to complete
            while not self.prereq_ready(run):
                print("waiting for prereq")
                await self.wait_completion()

            self._cores_used += run._simulation.resreq_cores()
            self._mem_used += run._simulation.resreq_mem()

            job = asyncio.create_task(self.do_run(run))
            self._pending_jobs.add(job)

        # wait for all runs to finish
        await asyncio.gather(*self._pending_jobs)

    async def start(self) -> None:
        """Execute all defined runs."""
        self._starter_task = asyncio.create_task(self.do_start())
        try:
            await self._starter_task
        except asyncio.CancelledError:
            for job in self._pending_jobs:
                job.cancel()
            # wait for all runs to finish
            await asyncio.gather(*self._pending_jobs)

    def interrupt_handler(self) -> None:
        self._starter_task.cancel()
