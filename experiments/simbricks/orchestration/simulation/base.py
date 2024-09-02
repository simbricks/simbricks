# Copyright 2024 Max Planck Institute for Software Systems, and
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
import abc
import typing as tp
import simbricks.orchestration.system as sys_conf
from simbricks.orchestration.experiment import experiment_environment_new as exp_env
from simbricks.orchestration.instantiation import base as inst_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.simulation import (
        Channel,
        HostSim,
        PCIDevSim,
        NetSim,
        base as sim_base,
    )


class Simulator(abc.ABC):
    """Base class for all simulators."""

    def __init__(
        self, simulation: sim_base.Simulation, relative_executable_path: str = ""
    ) -> None:
        self.extra_deps: list[Simulator] = []
        self.name: str = ""
        self.experiment: sim_base.Simulation = simulation
        self._components: set[sys_conf.Component] = []
        self._relative_executable_path: str = relative_executable_path

    @staticmethod
    def filter_sockets(
        sockets: list[inst_base.Socket],
        filter_type: inst_base.SockType = inst_base.SockType.LISTEN,
    ) -> list[inst_base.Socket]:
        res = filter(lambda sock: sock._type == filter_type, sockets)
        return res

    @staticmethod
    def split_sockets_by_type(
        sockets: list[inst_base.Socket],
    ) -> tuple[sockets : list[inst_base.Socket], sockets : list[inst_base.Socket]]:
        listen = Simulator.filter_sockets(
            sockets=sockets, filter_type=inst_base.SockType.LISTEN
        )
        connect = Simulator.filter_sockets(
            sockets=sockets, filter_type=inst_base.SockType.CONNECT
        )
        return listen, connect

    def resreq_cores(self) -> int:
        """
        Number of cores this simulator requires during execution.

        This is used for scheduling multiple runs and experiments.
        """
        return 1

    def resreq_mem(self) -> int:
        """
        Number of memory in MB this simulator requires during execution.

        This is used for scheduling multiple runs and experiments.
        """
        return 64

    def full_name(self) -> str:
        """Full name of the simulator."""
        return ""

    # pylint: disable=unused-argument
    def prep_cmds(self, env: exp_env.ExpEnv) -> list[str]:
        """Commands to prepare execution of this simulator."""
        return []

    def _add_component(self, comp: sys_base.Component) -> None:
        if comp in self._components:
            raise Exception("cannot add the same specification twice to a simulator")
        self._components.add(comp)
        self.experiment.add_spec_sim_map(comp, self)

    def _chan_needs_instance(self, chan: sys_conf.Channel) -> bool:
        if (
            chan.a.component in self._components
            and chan.b.component in self._components
        ):
            return False
        return True

    def _get_my_interface(self, chan: sys_conf.Channel) -> sys_conf.Interface:
        interface = None
        for inter in chan.interfaces():
            if inter.component in self._components:
                assert interface is None
                interface = inter
        if interface is None:
            raise Exception(
                "unable to find channel interface for simulators specification"
            )
        return interface

    def _get_sys_chan(self, interface: sys_conf.Interface) -> sys_conf.Channel:
        if not interface.is_connected():
            raise Exception("interface does not need a channel as it is not connected")
        return interface.channel

    def _get_socket_and_chan(
        self, inst: inst_base.Instantiation, interface: sys_conf.Interface
    ) -> tuple[sys_conf.Channel, inst_base.Socket] | tuple[None, None]:
        # get the channel associated with this interface
        chan = self._get_sys_chan(interface=interface)
        # check if interfaces channel is simulator internal, i.e. doesnt need an instanciation
        if not self._chan_needs_instance(chan):
            return None, None
        # create channel simualtion object
        channel = self.experiment.retrieve_or_create_channel(chan)
        # create the socket to listen on or connect to
        socket = inst.get_socket(interface=interface)
        return (channel, socket)

    def _get_channels_and_sockets(
        self, inst: inst_base.Instantiation
    ) -> tuple[list[sim_chan.Channel], list[inst_base.Socket]]:

        channels = []
        sockets = []

        for comp_spec in self._components:
            for interface in comp_spec.interfaces():

                channel, socket = self._get_socket_and_chan(
                    inst=inst, interface=interface
                )
                if channel is None or socket is None:
                    continue

                channels.append(channel)
                sockets.append(socket)

        return channels, sockets

    # pylint: disable=unused-argument
    @abc.abstractmethod
    def run_cmd(self, env: exp_env.ExpEnv) -> str:
        """Command to execute this simulator."""
        return ""

    def dependencies(self) -> list[Simulator]:
        """Other simulators to execute before this one."""
        return []

    # Sockets to be cleaned up: always the CONNECTING sockets
    # pylint: disable=unused-argument
    def sockets_cleanup(self, inst: inst_base.Instantiation) -> list[inst_base.Socket]:
        sockets = []
        for comp_spec in self._components:
            for interface in comp_spec.interfaces():
                socket = inst.get_socket(interface=interface)
                if socket._type == inst_base.SockType.CONNECT:
                    sockets.append(socket)

        return sockets

    # sockets to wait for indicating the simulator is ready
    # pylint: disable=unused-argument
    def sockets_wait(self, env: exp_env.ExpEnv) -> list[str]:
        return []

    def start_delay(self) -> int:
        return 5

    def wait_terminate(self) -> bool:
        return False


class Simulation(object):
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
        self.timeout: int | None = None
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
        self.hosts: list[HostSim] = []
        """The host simulators to run."""
        self.pcidevs: list[PCIDevSim] = []
        """The PCIe device simulators to run."""
        self.memdevs: list[MemDevSim] = []
        """The memory device simulators to run."""
        self.netmems: list[NetMemSim] = []
        """The network memory simulators to run."""
        self.networks: list[NetSim] = []
        """The network simulators to run."""
        self.metadata: dict[str, tp.Any] = {}

        self.sys_sim_map: dict[sys_conf.Component, Simulator] = {}
        """System component and its simulator pairs"""

        self._chan_map: dict[sys_conf.Channel, Channel] = {}
        """Channel spec and its instanciation"""

    def add_spec_sim_map(self, sys: sys_conf.Component, sim: Simulator):
        """Add a mapping from specification to simulation instance"""
        if sys in self.sys_sim_map:
            raise Exception("system component is already mapped by simulator")
        self.sys_sim_map[sys] = sim

    def is_channel_instantiated(self, chan: Channel) -> bool:
        return chan in self._chan_map

    def retrieve_or_create_channel(self, chan: sys_conf.Channel) -> Channel:
        if self.is_channel_instantiated(chan):
            return self._chan_map[chan]

        channel = Channel(self, chan)
        self._chan_map[chan] = channel
        return channel

    @property
    def nics(self):
        return filter(lambda pcidev: pcidev.is_nic(), self.pcidevs)

    def add_host(self, sim: HostSim) -> None:
        """Add a host simulator to the experiment."""
        for h in self.hosts:
            if h.name == sim.name:
                raise ValueError("Duplicate host name")
        self.hosts.append(sim)

    def add_nic(self, sim: NICSim | I40eMultiNIC):
        """Add a NIC simulator to the experiment."""
        self.add_pcidev(sim)

    def add_pcidev(self, sim: PCIDevSim) -> None:
        """Add a PCIe device simulator to the experiment."""
        for d in self.pcidevs:
            if d.name == sim.name:
                raise ValueError("Duplicate pcidev name")
        self.pcidevs.append(sim)

    def add_memdev(self, sim: simulators.MemDevSim):
        for d in self.memdevs:
            if d.name == sim.name:
                raise ValueError("Duplicate memdev name")
        self.memdevs.append(sim)

    def add_netmem(self, sim: simulators.NetMemSim):
        for d in self.netmems:
            if d.name == sim.name:
                raise ValueError("Duplicate netmems name")
        self.netmems.append(sim)

    def add_network(self, sim: NetSim) -> None:
        """Add a network simulator to the experiment."""
        for n in self.networks:
            if n.name == sim.name:
                raise ValueError("Duplicate net name")
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

    def find_sim(self, comp: sys_conf.Component) -> sim_base.Simulator:
        """Returns the used simulator object for the system component."""
        for c, sim in self.sys_sim_map.items():
            if c == comp:
                return sim

        raise Exception("Simulator Not Found")
