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
import traceback
import typing

from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.instantiation import dependency_topology as dep_topo
from simbricks.orchestration.instantiation import socket as inst_socket
from simbricks.orchestration.simulation import base as sim_base
from simbricks.runtime import command_executor as cmd_exec
from simbricks.runtime import output
from simbricks.utils import graphlib

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import proxy as inst_proxy


class SimulationExecutorCallbacks:

    def __init__(self, instantiation: inst_base.Instantiation) -> None:
        self._instantiation = instantiation
        self._output: output.SimulationOutput = output.SimulationOutput(
            self._instantiation.simulation
        )

    @property
    def output(self) -> output.SimulationOutput:
        return self._output

    # ---------------------------------------
    # Callbacks related to whole simulation -
    # ---------------------------------------

    async def simulation_started(self) -> None:
        self._output.set_start()

    async def simulation_prepare_cmd_start(self, cmd: str) -> None:
        self._output.add_generic_prepare_cmd(cmd)

    async def simulation_prepare_cmd_stdout(self, cmd: str, lines: list[str]) -> None:
        self._output.generic_prepare_cmd_stdout(cmd, lines)

    async def simulation_prepare_cmd_stderr(self, cmd: str, lines: list[str]) -> None:
        self._output.generic_prepare_cmd_stderr(cmd, lines)

    async def simulation_exited(self, state: output.SimulationExitState) -> None:
        self._output.set_end(state)

    # -----------------------------
    # Simulator-related callbacks -
    # -----------------------------

    async def simulator_prepare_started(self, sim: sim_base.Simulator, cmd: str) -> None:
        self._output.set_simulator_cmd(sim, cmd)

    async def simulator_prepare_exited(self, sim: sim_base.Simulator, exit_code: int) -> None:
        pass

    async def simulator_prepare_stdout(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        self._output.append_simulator_stdout(sim, lines)

    async def simulator_prepare_stderr(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        self._output.append_simulator_stderr(sim, lines)

    async def simulator_started(self, sim: sim_base.Simulator, cmd: str) -> None:
        self._output.set_simulator_cmd(sim, cmd)

    async def simulator_ready(self, sim: sim_base.Simulator) -> None:
        pass

    async def simulator_exited(self, sim: sim_base.Simulator, exit_code: int) -> None:
        pass

    async def simulator_stdout(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        self._output.append_simulator_stdout(sim, lines)

    async def simulator_stderr(self, sim: sim_base.Simulator, lines: list[str]) -> None:
        self._output.append_simulator_stderr(sim, lines)

    # -------------------------
    # Proxy-related callbacks -
    # -------------------------

    async def proxy_started(self, proxy: inst_proxy.Proxy, cmd: str) -> None:
        self._output.set_proxy_cmd(proxy, cmd)

    async def proxy_ready(self, proxy: inst_proxy.Proxy) -> None:
        pass

    async def proxy_exited(self, proxy: inst_proxy.Proxy, exit_code: int) -> None:
        pass

    async def proxy_stdout(self, proxy: inst_proxy.Proxy, lines: list[str]) -> None:
        self._output.append_proxy_stdout(proxy, lines)

    async def proxy_stderr(self, proxy: inst_proxy.Proxy, lines: list[str]) -> None:
        self._output.append_proxy_stderr(proxy, lines)


class SimulationExecutor:

    def __init__(
        self,
        instantiation: inst_base.Instantiation,
        callbacks: SimulationExecutorCallbacks,
        verbose: bool,
        profile_int=None,
    ) -> None:
        self._instantiation: inst_base.Instantiation = instantiation
        self._callbacks = callbacks
        self._verbose: bool = verbose
        self._profile_int: int | None = profile_int
        self._running_sims: dict[sim_base.Simulator, cmd_exec.CommandExecutor] = {}
        self._running_proxies: dict[inst_proxy.Proxy, cmd_exec.CommandExecutor] = {}
        self._wait_sims: list[cmd_exec.CommandExecutor] = []
        self._cmd_executor = cmd_exec.CommandExecutorFactory(callbacks)

    async def _start_proxy(self, proxy: inst_proxy.Proxy) -> None:
        """Start a proxy and wait for it to be ready."""
        cmd_exec = await self._cmd_executor.start_simulator(proxy, proxy.run_cmd())
        self._running_proxies[proxy] = cmd_exec

        # Wait till sockets exist
        wait_socks = proxy.sockets_wait(inst=self._instantiation)
        for sock in wait_socks:
            await sock.wait()
        self._callbacks.proxy_ready(proxy)

    async def _start_sim(self, sim: sim_base.Simulator) -> None:
        """Start a simulator and wait for it to be ready."""
        try:
            name = sim.full_name()
            cmd_exec = await self._cmd_executor.start_simulator(
                sim, sim.run_cmd(self._instantiation)
            )
            self._running_sims[sim] = cmd_exec

            # give simulator time to start if indicated
            delay = sim.start_delay()
            if delay > 0:
                await asyncio.sleep(delay)

            # Wait till sockets exist
            wait_socks = sim.sockets_wait(inst=self._instantiation)
            if len(wait_socks) > 0:
                if self._verbose:
                    print(f"{self._instantiation.simulation.name}: waiting for sockets {name}")
                for sock in wait_socks:
                    await sock.wait()
                if self._verbose:
                    print(
                        f"{self._instantiation.simulation.name}: waited successfully for sockets {name}"
                    )
            await self._callbacks.simulator_ready(sim)

            if sim.wait_terminate:
                self._wait_sims.append(cmd_exec)

        except asyncio.CancelledError:
            pass

    async def prepare(self) -> None:
        self._instantiation._cmd_executor = self._cmd_executor
        await self._instantiation.prepare()

    async def terminate_collect_sims(self) -> None:
        """Terminates all simulators and collects output."""
        if self._verbose:
            print(f"{self._instantiation.simulation.name}: cleaning up")

        # Interrupt, then terminate, then kill all processes. Do this in parallel so user does not
        # have to wait unnecessaryily long.
        scs = []
        for exec in itertools.chain(self._running_sims.values(), self._running_proxies.values()):
            scs.append(asyncio.create_task(exec.int_term_kill()))
        await asyncio.gather(*scs)

        # wait for all processes to terminate
        for exec in itertools.chain(self._running_sims.values(), self._running_proxies.values()):
            await exec.wait()

    async def sigusr1(self) -> None:
        for exec in self._running_sims.values():
            await exec.sigusr1()

    async def _profiler(self) -> None:
        assert self._profile_int
        while True:
            await asyncio.sleep(self._profile_int)
            await self.sigusr1()

    async def run(self) -> output.SimulationOutput:
        profiler_task = None

        starting: list[asyncio.Task] = []
        try:
            await self._callbacks.simulation_started()
            graph = self._instantiation.sim_dependencies()
            ts = graphlib.TopologicalSorter(graph)
            ts.prepare()
            while ts.is_active():
                # start ready simulators in parallel
                topo_comps = []
                for comp in ts.get_ready():
                    comp: dep_topo.TopologyComponent
                    match comp.type:
                        case dep_topo.TopologyComponentType.SIMULATOR:
                            starting.append(
                                asyncio.create_task(self._start_sim(comp.get_simulator()))
                            )
                        case dep_topo.TopologyComponentType.PROXY:
                            starting.append(
                                asyncio.create_task(self._start_proxy(comp.get_proxy()))
                            )
                        case _:
                            raise RuntimeError("Unhandled topology component type")
                    topo_comps.append(comp)

                # wait for starts to complete
                await asyncio.gather(*starting)

                for comp in topo_comps:
                    ts.done(comp)

            if self._profile_int:
                profiler_task = asyncio.create_task(self._profiler())

            # wait until all simulators indicated to be awaited exit
            for sc in self._wait_sims:
                await sc.wait()
            await self._callbacks.simulation_exited(output.SimulationExitState.SUCCESS)
        except asyncio.CancelledError:
            if self._verbose:
                print(f"{self._instantiation.simulation.name}: interrupted")
            await self._callbacks.simulation_exited(output.SimulationExitState.INTERRUPTED)
        except:  # pylint: disable=bare-except
            await self._callbacks.simulation_exited(output.SimulationExitState.FAILED)
            traceback.print_exc()

        if profiler_task:
            try:
                profiler_task.cancel()
            except asyncio.CancelledError:
                pass

        for task in starting:
            if not task.done():
                task.cancel()
                await task

        # The bare except above guarantees that we always execute the following
        # code, which terminates all simulators and produces a proper output
        # file.
        terminate_collect_task = asyncio.create_task(self.terminate_collect_sims())
        # prevent terminate_collect_task from being cancelled
        while True:
            try:
                await asyncio.shield(terminate_collect_task)
                return self._callbacks.output
            except asyncio.CancelledError as e:
                print(e)

    async def cleanup(self) -> None:
        await self._instantiation.cleanup()
