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

from __future__ import annotations

import asyncio
import itertools
import shlex
import traceback
import typing as tp
import abc

from simbricks.orchestration.utils import graphlib

from simbricks.orchestration.simulation import output
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.runtime_new import command_executor


class ExperimentBaseRunner(abc.ABC):

    def __init__(self, simulation: sim_base.Simulation, instantiation: inst_base.Instantiation, verbose: bool) -> None:
        self._simulation: sim_base.Simulation = simulation
        self._instantiation: inst_base.Instantiation = instantiation
        self._verbose: bool = verbose
        self._profile_int: int | None = None
        self._out = output.SimulationOutput(self._simulation)
        self._running: list[tuple[sim_base.Simulator, command_executor.SimpleComponent]] = []
        self._sockets: list[tuple[command_executor.Executor, inst_base.Socket]] = []
        self._wait_sims: list[command_executor.Component] = []

    @abc.abstractmethod
    def sim_executor(self, simulator: sim_base.Simulator) -> command_executor.Executor:
        pass

    def sim_graph(self) -> dict[sim_base.Simulator, set[sim_base.Simulator]]:
        sims = self._simulation.all_simulators()
        graph = {}
        for sim in sims:
            deps = sim.dependencies() + sim.extra_deps
            print(f'deps of {sim}: {sim.dependencies()}')
            graph[sim] = set()
            for d in deps:
                graph[sim].add(d)
        return graph

    async def start_sim(self, sim: sim_base.Simulator) -> None:
        """Start a simulator and wait for it to be ready."""

        name = sim.full_name()
        if self._verbose:
            print(f'{self._simulation.name}: starting {name}')

        run_cmd = sim.run_cmd(self._instantiation)
        if run_cmd is None:
            if self._verbose:
                print(f'{self._simulation.name}: started dummy {name}')
            return

        # run simulator
        executor = self.sim_executor(sim)
        sc = executor.create_component(
            name, shlex.split(run_cmd), verbose=self._verbose, canfail=True
        )
        await sc.start()
        self._running.append((sim, sc))

        # add sockets for cleanup
        for sock in sim.sockets_cleanup(inst=self._instantiation):
            self._sockets.append((executor, sock))

        # Wait till sockets exist
        wait_socks = sim.sockets_wait(inst=self._instantiation)
        if len(wait_socks) > 0:
            if self._verbose:
                print(f'{self._simulation.name}: waiting for sockets {name}')
            await self._instantiation.wait_for_sockets(executor=executor, sockets=wait_socks)
            if self._verbose:
                print(f'{self._simulation.name}: waited successfully for sockets {name}')

        # add time delay if required
        delay = sim.start_delay()
        if delay > 0:
            await asyncio.sleep(delay)

        if sim.wait_terminate():
            self._wait_sims.append(sc)

        if self.verbose:
            print(f'{self._simulation.name}: started {name}')

    async def before_wait(self) -> None:
        pass

    async def before_cleanup(self) -> None:
        pass

    async def after_cleanup(self) -> None:
        pass

    async def prepare(self) -> None:
        # generate config tars
        # copies = []
        # for host in self.exp.hosts:
        #     path = self.env.cfgtar_path(host)
        #     if self._verbose:
        #         print('preparing config tar:', path)
        #     # TODO: FIXME
        #     host.node_config.make_tar(self.env, path)
        #     executor = self.sim_executor(host)
        #     task = asyncio.create_task(executor.send_file(path, self._verbose))
        #     copies.append(task)
        # await asyncio.gather(*copies)

        # prepare all simulators in parallel
        sims = []
        for sim in self._simulation.all_simulators():
            sim.prep_tar(self._instantiation)
            prep_cmds = list(sim.prep_cmds(inst=self._instantiation))
            executor = self.sim_executor(sim)
            task = asyncio.create_task(
                executor.run_cmdlist(
                    'prepare_' + self._simulation.name, prep_cmds, verbose=self._verbose
                )
            )
            sims.append(task)
        await asyncio.gather(*sims)

    async def wait_for_sims(self) -> None:
        """Wait for simulators to terminate (the ones marked to wait on)."""
        if self._verbose:
            print(f'{self._simulation.name}: waiting for hosts to terminate')
        for sc in self._wait_sims:
            await sc.wait()

    async def terminate_collect_sims(self) -> output.SimulationOutput:
        """Terminates all simulators and collects output."""
        self._out.set_end()
        if self._verbose:
            print(f'{self._simulation.name}: cleaning up')

        await self.before_cleanup()

        # "interrupt, terminate, kill" all processes
        scs = []
        for _, sc in self._running:
            scs.append(asyncio.create_task(sc.int_term_kill()))
        await asyncio.gather(*scs)

        # wait for all processes to terminate
        for _, sc in self._running:
            await sc.wait()

        # remove all sockets
        await self._instantiation.cleanup_sockets(sockets=self._sockets)

        # add all simulator components to the output
        for sim, sc in self._running:
            self._out.add_sim(sim, sc)

        await self.after_cleanup()
        return self._out

    async def profiler(self):
        assert self._profile_int
        while True:
            await asyncio.sleep(self._profile_int)
            for (_, sc) in self._running:
                await sc.sigusr1()

    async def run(self) -> output.SimulationOutput:
        profiler_task = None

        try:
            self._out.set_start()
            graph = self.sim_graph()
            print(graph)
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

            if self._profile_int:
                profiler_task = asyncio.create_task(self.profiler())
            await self.before_wait()
            await self.wait_for_sims()
        except asyncio.CancelledError:
            if self._verbose:
                print(f'{self._simulation.name}: interrupted')
            self._out.set_interrupted()
        except:  # pylint: disable=bare-except
            self._out.set_failed()
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

    def __init__(self, executor: command_executor.Executor, *args, **kwargs) -> None:
        self._executor = executor
        super().__init__(*args, **kwargs)

    def sim_executor(self, sim: sim_base.Simulator) -> command_executor.Executor:
        return self._executor


# TODO: FIXME
class ExperimentDistributedRunner(ExperimentBaseRunner):
    """Simple experiment runner with just one executor."""

    # TODO: FIXME
    def __init__(
        self, execs, exp: DistributedExperiment, *args, **kwargs
    ) -> None:
        self.execs = execs
        super().__init__(exp, *args, **kwargs)
        self.exp = exp  # overrides the type in the base class
        assert self.exp.num_hosts <= len(execs)

    def sim_executor(self, sim) -> command_executor.Executor:
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
