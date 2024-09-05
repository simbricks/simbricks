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
import typing as tp

from simbricks.orchestration import proxy
from simbricks.orchestration.exectools import Executor
from simbricks.orchestration.experiments import DistributedExperiment, Experiment
from simbricks.orchestration.runtime_new import simulation_executor
from simbricks.orchestration.runtime_new.runs import base


class DistributedSimpleRuntime(base.Runtime):

    def __init__(self, executors, verbose=False) -> None:
        super().__init__()
        self.runnable: list[base.Run] = []
        self.complete: list[base.Run] = []
        self.verbose = verbose
        self.executors = executors

        self._running: asyncio.Task

    def add_run(self, run: base.Run) -> None:
        if not isinstance(run.experiment, DistributedExperiment):
            raise RuntimeError("Only distributed experiments supported")

        self.runnable.append(run)

    async def do_run(self, run: base.Run) -> None:
        runner = simulation_executor.ExperimentDistributedRunner(
            self.executors,
            # we ensure the correct type in add_run()
            tp.cast(DistributedExperiment, run.experiment),
            run.env,
            self.verbose,
        )
        if self.profile_int:
            runner.profile_int = self.profile_int

        try:
            for executor in self.executors:
                await run.prep_dirs(executor)
            await runner.prepare()
        except asyncio.CancelledError:
            # it is safe to just exit here because we are not running any
            # simulators yet
            return

        run.output = await runner.run()  # already handles CancelledError
        self.complete.append(run)

        # if the log is huge, this step takes some time
        if self.verbose:
            print(f"Writing collected output of run {run.name()} to JSON file ...")
        run.output.dump(run.outpath)

    async def start(self) -> None:
        for run in self.runnable:
            if self._interrupted:
                return

            self._running = asyncio.create_task(self.do_run(run))
            await self._running

    def interrupt_handler(self) -> None:
        if self._running:
            self._running.cancel()


# TODO: fix this function
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
