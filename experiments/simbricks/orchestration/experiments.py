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

import itertools
import typing as tp

from simbricks.orchestration.proxy import NetProxyConnecter, NetProxyListener
from simbricks.orchestration.simulators import (
    HostSim, I40eMultiNIC, NetSim, NICSim, PCIDevSim, MemDevSim, NetMemSim,
    Simulator
)


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
        self.memdevs: tp.List[MemDevSim] = []
        """The memory device simulators to run."""
        self.networks: tp.List[NetSim] = []
        """The network simulators to run."""
        self.metadata = {}

    @property
    def nics(self):
        return filter(lambda pcidev: pcidev.is_nic(), self.pcidevs)

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

    def add_memdev(self, sim: MemDevSim):
        for d in self.memdevs:
            if d.name == sim.name:
                raise Exception('Duplicate memdev name')
        self.memdevs.append(sim)

    def add_netmem(self, sim: NetMemSim):
        self.memdevs.append(sim)

    def add_network(self, sim: NetSim):
        for n in self.networks:
            if n.name == sim.name:
                raise Exception('Duplicate net name')
        self.networks.append(sim)

    def all_simulators(self):
        """All simulators used in experiment."""
        return itertools.chain(self.hosts, self.pcidevs, self.memdevs,
                self.networks)

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
