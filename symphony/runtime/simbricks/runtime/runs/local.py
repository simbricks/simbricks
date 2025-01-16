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
import typing

from simbricks.runtime import simulation_executor as sim_exec
from simbricks.runtime.runs import base as run_base
from simbricks.utils import artifatcs as art

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.instantiation import proxy as inst_proxy
    from simbricks.orchestration.simulation import base as sim_base


class LocalSimulationExecutorCallbacks(sim_exec.SimulationExecutorCallbacks):

    def __init__(self, instantiation: inst_base.Instantiation, verbose: bool):
        super().__init__(instantiation)
        self._instantiation = instantiation
        self._verbose = verbose

    # ---------------------------------------
    # Callbacks related to whole simulation -
    # ---------------------------------------

    async def simulation_prepare_cmd_start(self, cmd: str) -> None:
        await super().simulation_prepare_cmd_start(cmd)
        if self._verbose:
            print(f"+ [prepare] {cmd}")

    async def simulation_prepare_cmd_stdout(self, cmd: str, lines: list[str]) -> None:
        await super().simulation_prepare_cmd_stdout(cmd, lines)
        if self._verbose:
            for line in lines:
                print(f"[prepare] {line}")

    async def simulation_prepare_cmd_stderr(self, cmd: str, lines: list[str]) -> None:
        await super().simulation_prepare_cmd_stderr(cmd, lines)
        if self._verbose:
            for line in lines:
                print(f"[prepare] {line}")

    # -----------------------------
    # Simulator-related callbacks -
    # -----------------------------

    async def simulator_started(self, sim: sim_base.Simulator, cmd: str) -> None:
        await super().simulator_started(sim, cmd)
        if self._verbose:
            print(f"+ [{sim.full_name()}] {cmd}")

    async def simulator_exited(self, sim: sim_base.Simulator, exit_code: int) -> None:
        await super().simulator_exited(sim, exit_code)
        if self._verbose:
            print(f"- [{sim.full_name()}] exited with code {exit_code}")

    async def simulator_stdout(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        await super().simulator_stdout(sim, lines)
        if self._verbose:
            for line in lines:
                print(f"[{sim.full_name()}] {line}")

    async def simulator_stderr(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        await super().simulator_stderr(sim, lines)
        if self._verbose:
            for line in lines:
                print(f"[{sim.full_name()}] {line}")

    # -------------------------
    # Proxy-related callbacks -
    # -------------------------

    async def proxy_started(self, proxy: inst_proxy.Proxy, cmd: str) -> None:
        await super().proxy_started(proxy, cmd)
        if self._verbose:
            print(f"+ [{proxy.name}] {cmd}")

    async def proxy_exited(self, proxy: inst_proxy.Proxy, exit_code: int) -> None:
        await super().proxy_exited(proxy, exit_code)
        if self._verbose:
            print(f"- [{proxy.name}] exited with code {exit_code}")

    async def proxy_stdout(self, proxy: inst_proxy.Proxy, lines: list[str]) -> None:
        await super().proxy_stdout(proxy, lines)
        if self._verbose:
            for line in lines:
                print(f"[{proxy.name}] {line}")

    async def proxy_stderr(self, proxy: inst_proxy.Proxy, lines: list[str]) -> None:
        await super().proxy_stderr(proxy, lines)
        if self._verbose:
            for line in lines:
                print(f"[{proxy.name}] {line}")


class LocalSimpleRuntime(run_base.Runtime):
    """Execute runs locally in sequence."""

    def __init__(
        self,
        verbose=False,
    ):
        super().__init__()
        self._runnable: list[run_base.Run] = []
        self._complete: list[run_base.Run] = []
        self._verbose: bool = verbose
        self._running: asyncio.Task | None = None

    def add_run(self, run: run_base.Run) -> None:
        self._runnable.append(run)

    async def do_run(self, run: run_base.Run) -> None:
        """Actually executes `run`."""

        try:
            callbacks = LocalSimulationExecutorCallbacks(run.instantiation, self._verbose)
            sim_executor = sim_exec.SimulationExecutor(
                run.instantiation, callbacks, self._verbose, self._profile_int
            )
            await sim_executor.prepare()
        except asyncio.CancelledError:
            # it is safe to just exit here because we are not running any
            # simulators yet
            return

        run._output = await sim_executor.run()  # handles CancelledError
        self._complete.append(run)

        # if the log is huge, this step takes some time
        if self._verbose:
            print(f"Writing collected output of run {run.name()} to JSON file ...")

        # dump output into a file and then, before cleanup, create an artifact
        output_path = run.instantiation.get_simulation_output_path()
        run._output.dump(outpath=output_path)
        if run.instantiation.create_artifact:
            art.create_artifact(
                artifact_name=run.instantiation.artifact_name,
                paths_to_include=run.instantiation.artifact_paths,
            )

        await sim_executor.cleanup()

    async def start(self) -> None:
        """Execute the runs defined in `self.runnable`."""
        for run in self._runnable:
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

        self._pending_jobs: set[asyncio.Task] = set()
        self._starter_task: asyncio.Task

    def add_run(self, run: run_base.Run) -> None:
        if run.instantiation.simulation.resreq_cores() > self._cores:
            raise RuntimeError("Not enough cores available for run")

        if self._mem is not None and run.instantiation.simulation.resreq_mem() > self._mem:
            raise RuntimeError("Not enough memory available for run")

        if run._prereq is None:
            self._runs_noprereq.append(run)
        else:
            self._runs_prereq.append(run)

    async def do_run(self, run: run_base.Run) -> run_base.Run | None:
        """Actually executes `run`."""
        try:
            sim_executor = sim_exec.SimulationExecutor(run.instantiation, self._verbose)
            if self._profile_int is not None:
                sim_executor._profile_int = self._profile_int
            await sim_executor.prepare()
        except asyncio.CancelledError:
            # it is safe to just exit here because we are not running any
            # simulators yet
            return None

        print("starting run ", run.name())
        run._output = await sim_executor.run()  # already handles CancelledError

        # if the log is huge, this step takes some time
        if self._verbose:
            print(f"Writing collected output of run {run.name()} to JSON file ...")

        output_path = run.instantiation.get_simulation_output_path()
        run._output.dump(outpath=output_path)

        await sim_executor.cleanup()

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
            self._cores_used -= run.instantiation.simulation.resreq_cores()
            self._mem_used -= run.instantiation.simulation.resreq_mem()

    def enough_resources(self, run: run_base.Run) -> bool:
        """Check if enough cores and mem are available for the run."""
        simulation = run.instantiation.simulation  # pylint: disable=redefined-outer-name

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

            self._cores_used += run.instantiation.simulation.resreq_cores()
            self._mem_used += run.instantiation.simulation.resreq_mem()

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
