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
import functools
import itertools
import logging
import socket
import traceback
import typing

from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.instantiation import dependency_graph as dep_graph
from simbricks.orchestration.instantiation import process as inst_process
from simbricks.orchestration.instantiation import socket as inst_socket
from simbricks.orchestration.simulation import base as sim_base
from simbricks.runtime import command_executor as cmd_exec
from simbricks.runtime import output
from simbricks.utils import graphlib

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import proxy as inst_proxy


class ProxyReadyInfo:
    def __init__(self, id: int):
        self.id: int = id
        self.event: asyncio.Event = asyncio.Event()
        self.ip: str | None = None
        self.port: int | None = None


class SimulationExecutorCallbacks:
    def __init__(self, simulation: sim_base.Simulation) -> None:
        self._output: output.SimulationOutput = output.SimulationOutput(simulation)
        self.simulation_executor: SimulationExecutor
        """Set by the SimulationExecutor these callbacks are constructed with."""

    @property
    def simulation_output(self) -> output.SimulationOutput:
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

    async def simulation_message(self, level: int, msg: str) -> None:
        """Report a message produced by the runtime itself.

        Called from cancellation handlers, so implementations must not reach a
        suspension point.
        """
        self._output.add_runtime_message(level, msg)

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

    # ---------------------------
    # Process-related callbacks -
    # ---------------------------

    async def process_started(self, process: inst_process.FragmentProcess, cmd: str) -> None:
        self._output.set_process_cmd(process, cmd)

    async def process_ready(self, process: inst_process.FragmentProcess) -> None:
        pass

    async def process_exited(self, process: inst_process.FragmentProcess, exit_code: int) -> None:
        pass

    async def process_stdout(self, process: inst_process.FragmentProcess, lines: list[str]) -> None:
        self._output.append_process_stdout(process, lines)

    async def process_stderr(self, process: inst_process.FragmentProcess, lines: list[str]) -> None:
        self._output.append_process_stderr(process, lines)


class SimulationExecutor:
    def __init__(
        self,
        instantiation: inst_base.Instantiation,
        callbacks: SimulationExecutorCallbacks,
        verbose: bool,
        proxy_host_ip: str,
        profile_int=None,
    ) -> None:
        instantiation.command_executor = cmd_exec.CommandExecutorFactory(callbacks)
        callbacks.simulation_executor = self
        self._instantiation: inst_base.Instantiation = instantiation
        self._callbacks: SimulationExecutorCallbacks = callbacks
        self._verbose: bool = verbose
        self._proxy_host_ip: str = proxy_host_ip
        self._profile_int: int | None = profile_int
        self._running_sims: dict[sim_base.Simulator, cmd_exec.CommandExecutor] = {}
        self._running_proxies: dict[inst_proxy.Proxy, cmd_exec.CommandExecutor] = {}
        self._running_processes: dict[inst_process.FragmentProcess, cmd_exec.CommandExecutor] = {}
        self._wait_components: dict[int, asyncio.Event] = {}
        """Simulators and processes with `wait_terminate`, by id. The simulation ends once all of
        their events are set."""
        self._abort: asyncio.Event = asyncio.Event()
        """Set when a component failed in a way that must end the simulation."""
        self._abort_reason: str = ""
        self._stopping: bool = False
        """True while the simulation is being torn down, when process exits are expected."""
        self._external_proxy_running: dict[int, ProxyReadyInfo] = {}

    async def mark_external_proxies_running(self, id: int, ip: str, port: int):
        if id not in self._external_proxy_running:
            # Ignore external proxies that we do not depend on
            return
        proxy_info = self._external_proxy_running[id]
        if proxy_info.event.is_set():
            # We have already set the information for this external proxy
            return
        proxy_info.ip = ip
        proxy_info.port = port
        proxy_info.event.set()

    async def mark_simulator_terminated(self, id: int):
        if id in self._wait_components:
            self._wait_components[id].set()

    async def _process_exited(self, process: inst_process.FragmentProcess, exit_code: int) -> None:
        if process.id() in self._wait_components:
            self._wait_components[process.id()].set()
        if exit_code != 0 and process.fail_run_on_error and not self._stopping:
            self._abort_reason = f"process {process.name} exited with code {exit_code}"
            await self._callbacks.simulation_message(logging.ERROR, self._abort_reason)
            self._abort.set()

    async def _start_process(self, process: inst_process.FragmentProcess) -> None:
        """Start a fragment process and wait for it to be ready."""
        try:
            executor = self._instantiation.command_executor
            self._running_processes[process] = await executor.start_process(
                process,
                process.run_cmd(self._instantiation),
                exited=functools.partial(self._process_exited, process),
            )
            await process.wait_ready(self._instantiation)
            await self._callbacks.process_ready(process)
        except asyncio.CancelledError:
            pass

    async def _start_proxy(self, proxy: inst_proxy.Proxy) -> None:
        """Start a proxy and wait for it to be ready."""
        ip = ""
        try:
            ip = socket.gethostbyname(self._proxy_host_ip)
        except socket.gaierror:
            raise RuntimeError(
                f"could not resolve address '{self._proxy_host_ip}' for proxy {proxy.id}"
            )

        executor = self._instantiation.command_executor
        self._running_proxies[proxy] = await executor.start_proxy(
            proxy, proxy.run_cmd(self._instantiation, ip)
        )

        # Wait till sockets exist
        wait_socks = proxy.sockets_wait(inst=self._instantiation)
        for sock in wait_socks:
            await sock.wait()
        # Retrieve the port of a listening proxy
        if proxy._connection_mode == inst_socket.SockType.LISTEN:
            await proxy.read_listening_info()
            assert proxy._port is not None and proxy._port != 0
        await self._callbacks.proxy_ready(proxy)

    async def _wait_for_external_proxy(self, external_proxy: inst_proxy.Proxy) -> None:
        proxy_id = external_proxy.id()
        if proxy_id not in self._external_proxy_running:
            raise RuntimeError(f"could not find external proxy {proxy_id}")
        proxy_info = self._external_proxy_running[proxy_id]

        # Wait until the external proxy is ready
        await proxy_info.event.wait()

        assert proxy_info.ip is not None
        assert proxy_info.port is not None
        external_proxy._ip = proxy_info.ip
        external_proxy._port = proxy_info.port

    async def _start_sim(self, sim: sim_base.Simulator) -> None:
        """Start a simulator and wait for it to be ready."""
        try:
            name = sim.full_name()
            executor = self._instantiation.command_executor
            self._running_sims[sim] = await executor.start_simulator(
                sim, sim.run_cmd(self._instantiation)
            )

            # give simulator time to start if indicated
            delay = sim.start_delay()
            if delay > 0:
                await asyncio.sleep(delay)

            # Wait till sockets exist
            wait_socks = sim.sockets_wait(inst=self._instantiation)
            if len(wait_socks) > 0:
                await self._callbacks.simulation_message(
                    logging.DEBUG, f"waiting for sockets {name}"
                )
                for sock in wait_socks:
                    await sock.wait()
                await self._callbacks.simulation_message(
                    logging.DEBUG,
                    f"waited successfully for sockets {name}",
                )
            await self._callbacks.simulator_ready(sim)

        except asyncio.CancelledError:
            pass

    async def prepare(self) -> None:
        await self._instantiation.prepare()

        for sim in self._instantiation.simulation.all_simulators():
            # while a checkpoint is created every simulator that writes one has to finish it,
            # not only the ones with a waited-for application: killing a gem5 that is still
            # writing its checkpoint leaves a truncated one behind
            if sim.wait_terminate or (
                self._instantiation.create_checkpoint and sim.supports_checkpointing()
            ):
                self._wait_components[sim.id()] = asyncio.Event()
        for process in self._instantiation.assigned_fragment.all_processes():
            if process.wait_terminate:
                self._wait_components[process.id()] = asyncio.Event()

        if not self._wait_components:
            await self._callbacks.simulation_message(
                logging.WARNING,
                "warning: no component has a wait flag set, so the simulation terminates as"
                " soon as all simulators have started. Set wait_terminate on a simulator or"
                " wait on an application to wait for it.",
            )

    async def terminate_collect_sims(self) -> None:
        """Terminates all simulators, proxies and processes and collects output."""
        await self._callbacks.simulation_message(logging.DEBUG, "cleaning up")
        self._stopping = True

        with_sims = [
            exec
            for process, exec in self._running_processes.items()
            if process.stop == inst_process.StopPolicy.WITH_SIMULATORS
        ]
        after_sims = [
            (process, exec)
            for process, exec in self._running_processes.items()
            if process.stop == inst_process.StopPolicy.AFTER_SIMULATORS
        ]

        # Interrupt, then terminate, then kill all processes. Do this in parallel so user does not
        # have to wait unnecessaryily long.
        first_wave = list(
            itertools.chain(self._running_sims.values(), self._running_proxies.values(), with_sims)
        )
        scs = []
        for exec in first_wave:
            scs.append(asyncio.create_task(exec.int_term_kill()))
        await asyncio.gather(*scs)

        # wait for all processes to terminate
        for exec in first_wave:
            await exec.wait()

        # Processes that outlive the simulators, e.g. to finish reading what they produced, are
        # only interrupted now and get their grace period before being terminated.
        scs = []
        for process, exec in after_sims:
            scs.append(asyncio.create_task(exec.int_term_kill(delay=process.stop_grace_sec)))
        await asyncio.gather(*scs)
        for _, exec in after_sims:
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

            # add a ProxyReadyInfo mapping for each external proxy in the graph
            for node in graph:
                for dep in graph[node]:
                    if (
                        dep.type == dep_graph.SimulationDependencyNodeType.EXTERNAL_PROXY
                        and dep.get_proxy().id() not in self._external_proxy_running
                    ):
                        proxy_id = dep.get_proxy().id()
                        self._external_proxy_running[proxy_id] = ProxyReadyInfo(proxy_id)

            ts = graphlib.TopologicalSorter(graph)
            ts.prepare()
            while ts.is_active():
                # start ready simulators in parallel
                topo_comps = []
                for comp in ts.get_ready():
                    comp: dep_graph.SimulationDependencyNode
                    match comp.type:
                        case dep_graph.SimulationDependencyNodeType.SIMULATOR:
                            starting.append(
                                asyncio.create_task(self._start_sim(comp.get_simulator()))
                            )
                            topo_comps.append(comp)
                        case dep_graph.SimulationDependencyNodeType.PROXY:
                            starting.append(
                                asyncio.create_task(self._start_proxy(comp.get_proxy()))
                            )
                            topo_comps.append(comp)
                        case dep_graph.SimulationDependencyNodeType.EXTERNAL_PROXY:
                            starting.append(
                                asyncio.create_task(self._wait_for_external_proxy(comp.get_proxy()))
                            )
                            topo_comps.append(comp)
                        case dep_graph.SimulationDependencyNodeType.PROCESS:
                            starting.append(
                                asyncio.create_task(self._start_process(comp.get_process()))
                            )
                            topo_comps.append(comp)
                        case _:
                            raise RuntimeError("Unhandled topology component type")

                # wait for starts to complete
                await asyncio.gather(*starting)

                for comp in topo_comps:
                    ts.done(comp)

                # could happen when blocked by waiting for external proxy to start
                if not topo_comps:
                    await asyncio.sleep(3)

            if self._profile_int:
                profiler_task = asyncio.create_task(self._profiler())

            # wait until all components indicated to be awaited exit, or a component failed
            await self._wait_for_end()
            await self._callbacks.simulation_exited(output.SimulationExitState.SUCCESS)
        except asyncio.CancelledError:
            await self._callbacks.simulation_message(logging.DEBUG, "interrupted")
            await self._callbacks.simulation_exited(output.SimulationExitState.INTERRUPTED)
        except Exception:
            await self._callbacks.simulation_exited(output.SimulationExitState.FAILED)
            await self._callbacks.simulation_message(logging.ERROR, traceback.format_exc())

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
                return self._callbacks.simulation_output
            except asyncio.CancelledError as e:
                await self._callbacks.simulation_message(
                    logging.DEBUG,
                    f"cancelled while collecting simulator output: {e}",
                )

    async def _wait_for_end(self) -> None:

        async def all_waited() -> None:
            for event in self._wait_components.values():
                await event.wait()

        waited = asyncio.create_task(all_waited())
        aborted = asyncio.create_task(self._abort.wait())
        try:
            await asyncio.wait({waited, aborted}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in (waited, aborted):
                if not task.done():
                    task.cancel()
        if self._abort.is_set():
            raise RuntimeError(self._abort_reason)

    async def cleanup(self) -> None:
        await self._instantiation.cleanup()
