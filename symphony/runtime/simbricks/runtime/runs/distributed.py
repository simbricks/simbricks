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
import typing as tp

from simbricks.orchestration import proxy
from simbricks.orchestration.runtime_new import simulation_executor
from simbricks.orchestration.runtime_new import command_executor
from simbricks.orchestration.runtime_new.runs import base as run_base
from simbricks.orchestration.simulation import base as sim_base


class DistributedSimpleRuntime(run_base.Runtime):

    def __init__(
        self,
        executors: dict[sim_base.Simulator, command_executor.Executor],
        verbose: bool = False,
    ) -> None:
        super().__init__()
        self._runnable: list[run_base.Run] = []
        self._complete: list[run_base.Run] = []
        self._verbose: bool = verbose
        self._executors: dict[sim_base.Simulator, command_executor.Executor] = executors
        self._running: asyncio.Task | None = None

    def add_run(self, run: run_base.Run) -> None:
        # TODO: FIXME
        if not isinstance(run._simulation, DistributedExperiment):
            raise RuntimeError("Only distributed experiments supported")

        self._runnable.append(run)

    async def do_run(self, run: run_base.Run) -> None:
        # TODO: FIXME Distributed Experiments needs fixing
        runner = simulation_executor.ExperimentDistributedRunner(
            self._executors,
            # we ensure the correct type in add_run()
            tp.cast(DistributedExperiment, run._simulation),
            run._instantiation,
            self._verbose,
        )
        if self._profile_int:
            runner._profile_int = self._profile_int

        try:
            for executor in self._executors:
                await run.prep_dirs(executor)
            await runner.prepare()
        except asyncio.CancelledError:
            # it is safe to just exit here because we are not running any
            # simulators yet
            return

        run._output = await runner.run()  # already handles CancelledError
        self._complete.append(run)

        # if the log is huge, this step takes some time
        if self._verbose:
            print(f"Writing collected output of run {run.name()} to JSON file ...")

        output_path = run._instantiation.get_simulation_output_path(
            run_number=run._run_nr
        )
        run._output.dump(outpath=output_path)

    async def start(self) -> None:
        for run in self._runnable:
            if self._interrupted:
                return

            self._running = asyncio.create_task(self.do_run(run))
            await self._running

    def interrupt_handler(self) -> None:
        if self._running is not None:
            self._running.cancel()


# TODO: FIXME
def auto_dist(
    e: Experiment, execs: list[Executor], proxy_type: str = "sockets"
) -> DistributedExperiment:
    """
    Converts an Experiment into a DistributedExperiment.

    Assigns network to executor zero, and then round-robin assignment of hosts
    to executors, while also assigning all nics for a host to the same executor.
    """

    if len(execs) < 2:
        raise RuntimeError("auto_dist needs at least two hosts")
    elif len(execs) > 2:
        print("Warning: currently auto_dist only uses the first two hosts")

    if proxy_type == "sockets":
        proxy_listener_c = proxy.SocketsNetProxyListener
        proxy_connecter_c = proxy.SocketsNetProxyConnecter
    elif proxy_type == "rdma":
        proxy_listener_c = proxy.RDMANetProxyListener
        proxy_connecter_c = proxy.RDMANetProxyConnecter
    else:
        raise RuntimeError("Unknown proxy type specified")

    # Create the distributed experiment
    de = DistributedExperiment(e.name, 2)
    de.timeout = e.timeout
    de.checkpoint = e.checkpoint
    de.no_simbricks = e.no_simbricks
    de.metadata = e.metadata.copy()

    # create listening proxy on host 0
    lp = proxy_listener_c()
    lp.name = "listener"
    de.add_proxy(lp)
    de.assign_sim_host(lp, 0)

    # assign networks to first host
    for net in e.networks:
        de.add_network(net)
        de.assign_sim_host(net, 0)

    # create connecting proxy on host 1
    cp = proxy_connecter_c(lp)
    cp.name = "connecter"
    de.add_proxy(cp)
    de.assign_sim_host(cp, 1)

    # round-robin assignment for hosts
    k = 0
    for h in e.hosts:
        de.add_host(h)
        de.assign_sim_host(h, k)
        for nic in h.nics:
            de.assign_sim_host(nic, k)

            if k != 0:
                cp.add_nic(nic)
        k = (k + 1) % 2

    for nic in e.nics:
        de.add_nic(nic)

    return de
