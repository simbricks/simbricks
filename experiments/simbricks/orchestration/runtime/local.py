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

import asyncio
import pathlib
import typing as tp

from simbricks.orchestration import exectools
from simbricks.orchestration.runners import ExperimentSimpleRunner
from simbricks.orchestration.runtime.common import Run, Runtime


class LocalSimpleRuntime(Runtime):
    """Execute runs locally in sequence."""

    def __init__(
        self,
        verbose=False,
        executor: exectools.Executor = exectools.LocalExecutor()
    ):
        super().__init__()
        self.runnable: tp.List[Run] = []
        self.complete: tp.List[Run] = []
        self.verbose = verbose
        self.executor = executor
        self._running: tp.Optional[asyncio.Task] = None

    def add_run(self, run: Run):
        self.runnable.append(run)

    async def do_run(self, run: Run):
        """Actually executes `run`."""
        try:
            runner = ExperimentSimpleRunner(
                self.executor, run.experiment, run.env, self.verbose
            )
            await run.prep_dirs(self.executor)
            await runner.prepare()
        except asyncio.CancelledError:
            # it is safe to just exit here because we are not running any
            # simulators yet
            return

        run.output = await runner.run()  # already handles CancelledError
        self.complete.append(run)

        pathlib.Path(run.outpath).parent.mkdir(parents=True, exist_ok=True)
        with open(run.outpath, 'w', encoding='utf-8') as f:
            f.write(run.output.dumps())

    async def start(self):
        """Execute the runs defined in `self.runnable`."""
        for run in self.runnable:
            if self._interrupted:
                return

            self._running = asyncio.create_task(self.do_run(run))
            await self._running

    def interrupt(self):
        super().interrupt()
        if self._running:
            self._running.cancel()


class LocalParallelRuntime(Runtime):
    """Execute runs locally in parallel on multiple cores."""

    def __init__(
        self,
        cores: int,
        mem: tp.Optional[int] = None,
        verbose=False,
        executor: exectools.Executor = exectools.LocalExecutor()
    ):
        super().__init__()
        self.runs_noprereq: tp.List[Run] = []
        """Runs with no prerequesite runs."""
        self.runs_prereq: tp.List[Run] = []
        """Runs with prerequesite runs."""
        self.complete: tp.Set[Run] = set()
        self.cores = cores
        self.mem = mem
        self.verbose = verbose
        self.executor = executor

        self._pending_jobs: tp.Set[asyncio.Task] = set()
        self._starter_task: asyncio.Task

    def add_run(self, run: Run):
        if run.experiment.resreq_cores() > self.cores:
            raise Exception('Not enough cores available for run')

        if self.mem is not None and run.experiment.resreq_mem() > self.mem:
            raise Exception('Not enough memory available for run')

        if run.prereq is None:
            self.runs_noprereq.append(run)
        else:
            self.runs_prereq.append(run)

    async def do_run(self, run: Run):
        """Actually executes `run`."""
        try:
            runner = ExperimentSimpleRunner(
                self.executor, run.experiment, run.env, self.verbose
            )
            await run.prep_dirs(executor=self.executor)
            await runner.prepare()
        except asyncio.CancelledError:
            # it is safe to just exit here because we are not running any
            # simulators yet
            return

        print('starting run ', run.name())
        run.output = await runner.run()  # already handles CancelledError

        pathlib.Path(run.outpath).parent.mkdir(parents=True, exist_ok=True)
        with open(run.outpath, 'w', encoding='utf-8') as f:
            f.write(run.output.dumps())
        print('finished run ', run.name())
        return run

    async def wait_completion(self):
        """Wait for any run to terminate and return."""
        assert self._pending_jobs

        done, self._pending_jobs = await asyncio.wait(
            self._pending_jobs, return_when=asyncio.FIRST_COMPLETED
        )

        for run in done:
            run = await run
            self.complete.add(run)
            self.cores_used -= run.experiment.resreq_cores()
            self.mem_used -= run.experiment.resreq_mem()

    def enough_resources(self, run: Run):
        """Check if enough cores and mem are available for the run."""
        exp = run.experiment  # pylint: disable=redefined-outer-name

        if self.cores is not None:
            enough_cores = (self.cores - self.cores_used) >= exp.resreq_cores()
        else:
            enough_cores = True

        if self.mem is not None:
            enough_mem = (self.mem - self.mem_used) >= exp.resreq_mem()
        else:
            enough_mem = True

        return enough_cores and enough_mem

    def prereq_ready(self, run: Run):
        """Check if the prerequesite run for `run` has completed."""
        if run.prereq is None:
            return True

        return run.prereq in self.complete

    async def do_start(self):
        """Asynchronously execute the runs defined in `self.runs_noprereq +
        self.runs_prereq."""
        #self.completions = asyncio.Queue()
        self.cores_used = 0
        self.mem_used = 0

        runs = self.runs_noprereq + self.runs_prereq
        for run in runs:
            # if necessary, wait for enough memory or cores
            while not self.enough_resources(run):
                print('waiting for resources')
                await self.wait_completion()

            # if necessary, wait for prerequesite runs to complete
            while not self.prereq_ready(run):
                print('waiting for prereq')
                await self.wait_completion()

            self.cores_used += run.experiment.resreq_cores()
            self.mem_used += run.experiment.resreq_mem()

            job = asyncio.create_task(self.do_run(run))
            self._pending_jobs.add(job)

        # wait for all runs to finish
        await asyncio.wait(self._pending_jobs)

    async def start(self):
        """Execute all defined runs."""
        self._starter_task = asyncio.create_task(self.do_start())
        try:
            await self._starter_task
        except asyncio.CancelledError:
            for job in self._pending_jobs:
                job.cancel()
            # wait for all runs to finish
            await asyncio.wait(self._pending_jobs)

    def interrupt(self):
        super().interrupt()
        self._starter_task.cancel()
