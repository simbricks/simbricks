# Copyright 2022 Max Planck Institute for Software Systems, and
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
import itertools
import shlex
import traceback
import typing as tp
from abc import ABC, abstractmethod

from simbricks.orchestration.exectools import (
    Component, Executor, SimpleComponent
)
from simbricks.orchestration.experiment.experiment_environment import ExpEnv
from simbricks.orchestration.experiment.experiment_output import ExpOutput
from simbricks.orchestration.experiments import (
    DistributedExperiment, Experiment
)
from simbricks.orchestration.simulators import Simulator
from simbricks.orchestration.utils import graphlib


class ExperimentBaseRunner(ABC):

    def __init__(self, exp: Experiment, env: ExpEnv, verbose: bool) -> None:
        self.exp = exp
        self.env = env
        self.verbose = verbose
        self.profile_int: tp.Optional[int] = None
        self.out = ExpOutput(exp)
        self.running: tp.List[tp.Tuple[Simulator, SimpleComponent]] = []
        self.sockets: tp.List[tp.Tuple[Executor, str]] = []
        self.wait_sims: tp.List[Component] = []

    @abstractmethod
    def sim_executor(self, sim: Simulator) -> Executor:
        pass

    def sim_graph(self) -> tp.Dict[Simulator, tp.Set[Simulator]]:
        sims = self.exp.all_simulators()
        graph = {}
        for sim in sims:
            deps = sim.dependencies() + sim.extra_deps
            graph[sim] = set()
            for d in deps:
                graph[sim].add(d)
        return graph

    async def start_sim(self, sim: Simulator) -> None:
        """Start a simulator and wait for it to be ready."""

        name = sim.full_name()
        if self.verbose:
            print(f'{self.exp.name}: starting {name}')

        run_cmd = sim.run_cmd(self.env)
        if run_cmd is None:
            if self.verbose:
                print(f'{self.exp.name}: started dummy {name}')
            return

        # run simulator
        executor = self.sim_executor(sim)
        sc = executor.create_component(
            name, shlex.split(run_cmd), verbose=self.verbose, canfail=True
        )
        await sc.start()
        self.running.append((sim, sc))

        # add sockets for cleanup
        for s in sim.sockets_cleanup(self.env):
            self.sockets.append((executor, s))

        # Wait till sockets exist
        wait_socks = sim.sockets_wait(self.env)
        if wait_socks:
            if self.verbose:
                print(f'{self.exp.name}: waiting for sockets {name}')

            await executor.await_files(wait_socks, verbose=self.verbose)

        # add time delay if required
        delay = sim.start_delay()
        if delay > 0:
            await asyncio.sleep(delay)

        if sim.wait_terminate(self.env):
            self.wait_sims.append(sc)

        if self.verbose:
            print(f'{self.exp.name}: started {name}')

    async def before_wait(self) -> None:
        pass

    async def before_cleanup(self) -> None:
        pass

    async def after_cleanup(self) -> None:
        pass

    async def prepare(self) -> None:
        # generate config tars
        copies = []
        for host in self.exp.hosts:
            path = self.env.cfgtar_path(host)
            if self.verbose:
                print('preparing config tar:', path)
            host.node_config.make_tar(path)
            executor = self.sim_executor(host)
            task = asyncio.create_task(executor.send_file(path, self.verbose))
            copies.append(task)
        await asyncio.gather(*copies)

        # prepare all simulators in parallel
        sims = []
        for sim in self.exp.all_simulators():
            prep_cmds = list(sim.prep_cmds(self.env))
            executor = self.sim_executor(sim)
            task = asyncio.create_task(
                executor.run_cmdlist(
                    'prepare_' + self.exp.name, prep_cmds, verbose=self.verbose
                )
            )
            sims.append(task)
        await asyncio.gather(*sims)

    async def wait_for_sims(self) -> None:
        """Wait for simulators to terminate (the ones marked to wait on)."""
        if self.verbose:
            print(f'{self.exp.name}: waiting for hosts to terminate')
        for sc in self.wait_sims:
            await sc.wait()

    async def terminate_collect_sims(self) -> ExpOutput:
        """Terminates all simulators and collects output."""
        self.out.set_end()
        if self.verbose:
            print(f'{self.exp.name}: cleaning up')

        await self.before_cleanup()

        # "interrupt, terminate, kill" all processes
        scs = []
        for _, sc in self.running:
            scs.append(asyncio.create_task(sc.int_term_kill()))
        await asyncio.gather(*scs)

        # wait for all processes to terminate
        for _, sc in self.running:
            await sc.wait()

        # remove all sockets
        scs = []
        for (executor, sock) in self.sockets:
            scs.append(asyncio.create_task(executor.rmtree(sock)))
        if scs:
            await asyncio.gather(*scs)

        # add all simulator components to the output
        for sim, sc in self.running:
            self.out.add_sim(sim, sc)

        await self.after_cleanup()
        return self.out

    async def profiler(self):
        assert self.profile_int
        while True:
            await asyncio.sleep(self.profile_int)
            for (_, sc) in self.running:
                await sc.sigusr1()

    async def run(self) -> ExpOutput:
        profiler_task = None

        try:
            self.out.set_start()
            graph = self.sim_graph()
            ts = graphlib.TopologicalSorter(graph)
            ts.prepare()
            while ts.is_active():
                # start ready simulators in parallel
                starting = []
                sims = []
                for sim in ts.get_ready():
                    starting.append(asyncio.create_task(self.start_sim(sim)))
                    sims.append(sim)

                # wait for starts to complete
                await asyncio.gather(*starting)

                for sim in sims:
                    ts.done(sim)

            if self.profile_int:
                profiler_task = asyncio.create_task(self.profiler())
            await self.before_wait()
            await self.wait_for_sims()
        except asyncio.CancelledError:
            if self.verbose:
                print(f'{self.exp.name}: interrupted')
            self.out.set_interrupted()
        except:  # pylint: disable=bare-except
            self.out.set_failed()
            traceback.print_exc()

        if profiler_task:
            try:
                profiler_task.cancel()
            except asyncio.CancelledError:
                pass
        # The bare except above guarantees that we always execute the following
        # code, which terminates all simulators and produces a proper output
        # file.
        terminate_collect_task = asyncio.create_task(
            self.terminate_collect_sims()
        )
        # prevent terminate_collect_task from being cancelled
        while True:
            try:
                return await asyncio.shield(terminate_collect_task)
            except asyncio.CancelledError as e:
                print(e)
                pass


class ExperimentSimpleRunner(ExperimentBaseRunner):
    """Simple experiment runner with just one executor."""

    def __init__(self, executor: Executor, *args, **kwargs) -> None:
        self.executor = executor
        super().__init__(*args, **kwargs)

    def sim_executor(self, sim: Simulator) -> Executor:
        return self.executor


class ExperimentDistributedRunner(ExperimentBaseRunner):
    """Simple experiment runner with just one executor."""

    def __init__(
        self, execs, exp: DistributedExperiment, *args, **kwargs
    ) -> None:
        self.execs = execs
        super().__init__(exp, *args, **kwargs)
        self.exp = exp  # overrides the type in the base class
        assert self.exp.num_hosts <= len(execs)

    def sim_executor(self, sim) -> Executor:
        h_id = self.exp.host_mapping[sim]
        return self.execs[h_id]

    async def prepare(self) -> None:
        # make sure all simulators are assigned to an executor
        assert self.exp.all_sims_assigned()

        # set IP addresses for proxies based on assigned executors
        for p in itertools.chain(
            self.exp.proxies_listen, self.exp.proxies_connect
        ):
            executor = self.sim_executor(p)
            p.ip = executor.ip

        await super().prepare()
