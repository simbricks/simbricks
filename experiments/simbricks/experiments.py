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
import itertools
import shlex
import traceback
import typing as tp
from abc import ABC, abstractmethod

from simbricks.exectools import Executor, SimpleComponent
from simbricks.experiment.experiment_environment import ExpEnv
from simbricks.experiment.experiment_output import ExpOutput
from simbricks.proxy import NetProxyConnecter, NetProxyListener
from simbricks.simulators import (
    HostSim, I40eMultiNIC, NetSim, NICSim, PCIDevSim, Simulator
)
from simbricks.utils import graphlib


class Experiment(object):
    """Base class for all simulation experiments."""

    def __init__(self, name: str):
        self.name = name
        """
        This experiment's name. Can be used to run only a selection of
        experiments.
        """
        self.timeout: tp.Optional[int] = None
        """Timeout for experiment in seconds."""
        self.checkpoint = False
        """Whether to use checkpoints in the experiment.

        Using this property we can, for example, speed up booting a host
        simulator by first running in a less accurate mode. Before we then start
        the measurement we are interested in, a checkpoint is taken, the
        simulator shut down and finally restored in the accurate mode using this
        checkpoint."""
        self.no_simbricks = False
        """If `true`, no simbricks adapters are used in any of the
        simulators."""
        self.hosts: tp.List[HostSim] = []
        """The host simulators to run."""
        self.pcidevs: tp.List[PCIDevSim] = []
        """The PCIe device simulators to run."""
        self.networks: tp.List[NetSim] = []
        """The network simulators to run."""
        self.metadata = {}

    def add_host(self, sim: HostSim):
        for h in self.hosts:
            if h.name == sim.name:
                raise Exception('Duplicate host name')
        self.hosts.append(sim)

    def add_nic(self, sim: tp.Union[NICSim, I40eMultiNIC]):
        self.add_pcidev(sim)

    def add_pcidev(self, sim: PCIDevSim):
        for d in self.pcidevs:
            if d.name == sim.name:
                raise Exception('Duplicate pcidev name')
        self.pcidevs.append(sim)

    def add_network(self, sim: NetSim):
        for n in self.networks:
            if n.name == sim.name:
                raise Exception('Duplicate net name')
        self.networks.append(sim)

    def all_simulators(self):
        """All simulators used in experiment."""
        return itertools.chain(self.hosts, self.pcidevs, self.networks)

    def resreq_mem(self):
        """Memory required to run all simulators used in this experiment."""
        mem = 0
        for s in self.all_simulators():
            mem += s.resreq_mem()
        return mem

    def resreq_cores(self):
        """Number of Cores required to run all simulators used in this
        experiment."""
        cores = 0
        for s in self.all_simulators():
            cores += s.resreq_cores()
        return cores


class DistributedExperiment(Experiment):
    """Describes a distributed simulation experiment."""

    def __init__(self, name: str, num_hosts: int):
        super().__init__(name)
        self.num_hosts = num_hosts
        """Number of hosts to use."""
        self.host_mapping: tp.Dict[Simulator, int] = {}
        """Mapping from simulator to host ID."""
        self.proxies_listen: tp.List[NetProxyListener] = []
        self.proxies_connect: tp.List[NetProxyConnecter] = []

    def add_proxy(self, proxy: tp.Union[NetProxyListener, NetProxyConnecter]):
        if proxy.listen:
            self.proxies_listen.append(tp.cast(NetProxyListener, proxy))
        else:
            self.proxies_connect.append(tp.cast(NetProxyConnecter, proxy))

    def all_simulators(self):
        return itertools.chain(
            super().all_simulators(), self.proxies_listen, self.proxies_connect
        )

    def assign_sim_host(self, sim: Simulator, host: int):
        """Assign host ID (< self.num_hosts) for a simulator."""
        assert 0 <= host < self.num_hosts
        self.host_mapping[sim] = host

    def all_sims_assigned(self):
        """Check if all simulators are assigned to a host."""
        for s in self.all_simulators():
            if s not in self.host_mapping:
                return False
        return True


class ExperimentBaseRunner(ABC):

    def __init__(self, exp: Experiment, env: ExpEnv, verbose: bool):
        self.exp = exp
        self.env = env
        self.verbose = verbose
        self.out = ExpOutput(exp)
        self.running: tp.List[tp.Tuple[Simulator, SimpleComponent]] = []
        self.sockets = []
        self.wait_sims = []

    @abstractmethod
    def sim_executor(self, sim: Simulator) -> Executor:
        pass

    def sim_graph(self):
        sims = self.exp.all_simulators()
        graph = {}
        for sim in sims:
            deps = sim.dependencies() + sim.extra_deps
            graph[sim] = set()
            for d in deps:
                graph[sim].add(d)
        return graph

    async def start_sim(self, sim: Simulator):
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

        if sim.wait_terminate():
            self.wait_sims.append(sc)

        if self.verbose:
            print(f'{self.exp.name}: started {name}')

    async def before_wait(self):
        pass

    async def before_cleanup(self):
        pass

    async def after_cleanup(self):
        pass

    async def prepare(self):
        # generate config tars
        copies = []
        for host in self.exp.hosts:
            path = self.env.cfgtar_path(host)
            if self.verbose:
                print('preparing config tar:', path)
            host.node_config.make_tar(path)
            copies.append(self.sim_executor(host).send_file(path, self.verbose))
        await asyncio.wait(copies)

        # prepare all simulators in parallel
        sims = []
        for sim in self.exp.all_simulators():
            prep_cmds = list(sim.prep_cmds(self.env))
            executor = self.sim_executor(sim)
            sims.append(
                executor.run_cmdlist(
                    'prepare_' + self.exp.name, prep_cmds, verbose=self.verbose
                )
            )
        await asyncio.wait(sims)

    async def wait_for_sims(self):
        """Wait for simulators to terminate (the ones marked to wait on)."""
        if self.verbose:
            print(f'{self.exp.name}: waiting for hosts to terminate')
        for sc in self.wait_sims:
            await sc.wait()

    async def run(self):
        try:
            self.out.set_start()

            graph = self.sim_graph()
            ts = graphlib.TopologicalSorter(graph)
            ts.prepare()
            while ts.is_active():
                # start ready simulators in parallel
                starts = []
                sims = []
                for sim in ts.get_ready():
                    starts.append(self.start_sim(sim))
                    sims.append(sim)

                # wait for starts to complete
                await asyncio.wait(starts)

                for sim in sims:
                    ts.done(sim)

            await self.before_wait()
            await self.wait_for_sims()
        except:  # pylint: disable=bare-except
            self.out.set_failed()
            traceback.print_exc()

        finally:
            self.out.set_end()

            # shut things back down
            if self.verbose:
                print(f'{self.exp.name}: cleaning up')

            await self.before_cleanup()

            # "interrupt, terminate, kill" all processes
            scs = []
            for _, sc in self.running:
                scs.append(sc.int_term_kill())
            await asyncio.wait(scs)

            # wait for all processes to terminate
            for _, sc in self.running:
                await sc.wait()

            # remove all sockets
            scs = []
            for (executor, sock) in self.sockets:
                scs.append(executor.rmtree(sock))
            if scs:
                await asyncio.wait(scs)

            # add all simulator components to the output
            for sim, sc in self.running:
                self.out.add_sim(sim, sc)

            await self.after_cleanup()
        return self.out


class ExperimentSimpleRunner(ExperimentBaseRunner):
    """Simple experiment runner with just one executor."""

    def __init__(self, executor: Executor, *args, **kwargs):
        self.executor = executor
        super().__init__(*args, **kwargs)

    def sim_executor(self, sim: Simulator):
        return self.executor


class ExperimentDistributedRunner(ExperimentBaseRunner):
    """Simple experiment runner with just one executor."""

    def __init__(self, execs, exp: DistributedExperiment, *args, **kwargs):
        self.execs = execs
        super().__init__(exp, *args, **kwargs)
        self.exp = exp  # overrides the type in the base class
        assert self.exp.num_hosts <= len(execs)

    def sim_executor(self, sim):
        h_id = self.exp.host_mapping[sim]
        return self.execs[h_id]

    async def prepare(self):
        # make sure all simulators are assigned to an executor
        assert self.exp.all_sims_assigned()

        # set IP addresses for proxies based on assigned executors
        for p in itertools.chain(
            self.exp.proxies_listen, self.exp.proxies_connect
        ):
            executor = self.sim_executor(p)
            p.ip = executor.ip

        await super().prepare()
