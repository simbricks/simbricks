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

from simbricks.orchestration import simulators
import simbricks.orchestration.simulation as simulation
import simbricks.orchestration.system as system
from simbricks.orchestration.proxy import NetProxyConnecter, NetProxyListener
from simbricks.orchestration.simulators import (
    HostSim, I40eMultiNIC, NetSim, NICSim, PCIDevSim, Simulator
)


class Experiment(object):
    """
    Base class for all simulation experiments.

    Contains the simulators to be run and experiment-wide parameters.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        """
        This experiment's name.

        Can be used to run only a selection of experiments.
        """
        self.timeout: tp.Optional[int] = None
        """Timeout for experiment in seconds."""
        self.checkpoint = False
        """
        Whether to use checkpoint and restore for simulators.

        The most common use-case for this is accelerating host simulator startup
        by first running in a less accurate mode, then checkpointing the system
        state after boot and running simulations from there.
        """
        self.no_simbricks = False
        """If `true`, no simbricks adapters are used in any of the
        simulators."""
        self.hosts: tp.List[HostSim] = []
        """The host simulators to run."""
        self.pcidevs: tp.List[PCIDevSim] = []
        """The PCIe device simulators to run."""
        self.memdevs: tp.List[simulators.MemDevSim] = []
        """The memory device simulators to run."""
        self.netmems: tp.List[simulators.NetMemSim] = []
        """The network memory simulators to run."""
        self.networks: tp.List[NetSim] = []
        """The network simulators to run."""
        self.metadata: tp.Dict[str, tp.Any] = {}

        self.sys_sim_map: tp.Dict[system.Component, simulation.Simulator] = {}
        """System component and its simulator pairs"""

    @property
    def nics(self):
        return filter(lambda pcidev: pcidev.is_nic(), self.pcidevs)

    def add_host(self, sim: HostSim) -> None:
        """Add a host simulator to the experiment."""
        for h in self.hosts:
            if h.name == sim.name:
                raise ValueError('Duplicate host name')
        self.hosts.append(sim)

    def add_nic(self, sim: tp.Union[NICSim, I40eMultiNIC]):
        """Add a NIC simulator to the experiment."""
        self.add_pcidev(sim)

    def add_pcidev(self, sim: PCIDevSim) -> None:
        """Add a PCIe device simulator to the experiment."""
        for d in self.pcidevs:
            if d.name == sim.name:
                raise ValueError('Duplicate pcidev name')
        self.pcidevs.append(sim)

    def add_memdev(self, sim: simulators.MemDevSim):
        for d in self.memdevs:
            if d.name == sim.name:
                raise ValueError('Duplicate memdev name')
        self.memdevs.append(sim)

    def add_netmem(self, sim: simulators.NetMemSim):
        for d in self.netmems:
            if d.name == sim.name:
                raise ValueError('Duplicate netmems name')
        self.netmems.append(sim)

    def add_network(self, sim: NetSim) -> None:
        """Add a network simulator to the experiment."""
        for n in self.networks:
            if n.name == sim.name:
                raise ValueError('Duplicate net name')
        self.networks.append(sim)

    def all_simulators(self) -> tp.Iterable[Simulator]:
        """Returns all simulators defined to run in this experiment."""
        return itertools.chain(
            self.hosts, self.pcidevs, self.memdevs, self.netmems, self.networks
        )

    def resreq_mem(self) -> int:
        """Memory required to run all simulators in this experiment."""
        mem = 0
        for s in self.all_simulators():
            mem += s.resreq_mem()
        return mem

    def resreq_cores(self) -> int:
        """Number of Cores required to run all simulators in this experiment."""
        cores = 0
        for s in self.all_simulators():
            cores += s.resreq_cores()
        return cores


class DistributedExperiment(Experiment):
    """Describes a distributed simulation experiment."""

    def __init__(self, name: str, num_hosts: int) -> None:
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

    def all_simulators(self) -> tp.Iterable[Simulator]:
        return itertools.chain(
            super().all_simulators(), self.proxies_listen, self.proxies_connect
        )

    def assign_sim_host(self, sim: Simulator, host: int) -> None:
        """Assign host ID (< self.num_hosts) for a simulator."""
        assert 0 <= host < self.num_hosts
        self.host_mapping[sim] = host

    def all_sims_assigned(self) -> bool:
        """Check if all simulators are assigned to a host."""
        for s in self.all_simulators():
            if s not in self.host_mapping:
                return False
        return True
