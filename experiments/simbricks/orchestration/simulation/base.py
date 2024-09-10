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
import itertools
import time
import typing as tp
import simbricks.orchestration.system as sys_conf
import simbricks.orchestration.system.host as sys_host_conf
import simbricks.orchestration.instantiation.base as inst_base
import simbricks.orchestration.simulation.channel as sim_chan
import simbricks.orchestration.utils.base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.simulation import (
        Channel,
        HostSim,
        PCIDevSim,
        NetSim,
        base as sim_base,
    )


class Simulator(utils_base.IdObj):
    """Base class for all simulators."""

    def __init__(
        self,
        simulation: sim_base.Simulation,
        name: str = "",
        relative_executable_path: str = "",
    ) -> None:
        super().__init__()
        self.name: str = name
        self._relative_executable_path: str = relative_executable_path
        self.extra_deps: list[Simulator] = []
        self._simulation: sim_base.Simulation = simulation
        self._components: set[sys_conf.Component] = set()

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

    # helper method for simulators that do not support
    # multiple sync periods etc. Should become eventually
    # at some point in the future...
    @staticmethod
    def get_unique_latency_period_sync(
        channels: list[sim_chan.Channel],
    ) -> tuple[int, int, bool]:
        eth_latency = None
        sync_period = None
        run_sync = False
        for channel in channels:
            sync_period = min(sync_period, channel.sync_period)
            run_sync = run_sync or channel._synchronized
            eth_latency = max(eth_latency, channel.sys_channel.eth_latency)
        if eth_latency is None or sync_period is None:
            raise Exception("could not determine eth_latency and sync_period")
        return eth_latency, sync_period, sync

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
    def prep_cmds(self, inst: inst_base.Instantiation) -> list[str]:
        """Commands to prepare execution of this simulator."""
        return []

    def add(self, comp: sys_base.Component) -> None:
        if comp in self._components:
            raise Exception("cannot add the same specification twice to a simulator")
        self._components.add(comp)
        self._simulation.add_spec_sim_map(comp, self)

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

    def _get_socket(
        self, inst: inst_base.Instantiation, interface: sys_conf.Interface
    ) -> inst_base.Socket | None:
        # get the channel associated with this interface
        chan = self._get_sys_chan(interface=interface)
        # check if interfaces channel is simulator internal, i.e. doesnt need an instanciation
        if not self._chan_needs_instance(chan):
            return None
        # create the socket to listen on or connect to
        socket = inst.get_socket(
            interface=interface, supported_sock_types=self.supported_socket_types()
        )
        return socket

    def _get_sockets(self, inst: inst_base.Instantiation) -> list[inst_base.Socket]:
        sockets = []
        for comp_spec in self._components:
            for interface in comp_spec.interfaces():
                socket = self._get_socket(inst=inst, interface=interface)
                if socket is None:
                    continue
                sockets.append(socket)
        return sockets

    def _get_all_sockets_by_type(
        self, inst: inst_base.Instantiation, sock_type: inst_base.SockType
    ) -> list[inst_base.Socket]:
        sockets = self._get_sockets(inst=inst)
        sockets = Simulator.filter_sockets(sockets=sockets, filter_type=sock_type)
        return sockets

    def _get_channel(self, chan: sys_conf.Channel) -> sim_chan.Channel | None:
        if self._chan_needs_instance(chan):
            return self.experiment.retrieve_or_create_channel(chan=chan)
        return None

    def _get_channels(self, inst: inst_base.Instantiation) -> list[sim_chan.Channel]:
        channels = []
        for comp_spec in self._components:
            for chan in self.experiment.retrieve_or_create_channel(chan=chan):
                channel = self._get_channel(chan=chan)
                if channel is None:
                    continue
                channels.append(channel)
        return channels

    # pylint: disable=unused-argument
    @abc.abstractmethod
    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        """Command to execute this simulator."""
        return ""

    # TODO: FIXME
    def dependencies(self) -> list[Simulator]:
        """Other simulators to execute before this one."""
        return []

    # TODO: overwrite in sub-classes to reflect that currently not all adapters support both listening and connecting
    # In future version adapters should support both which would render this method obsolete
    # TODO: FIXME, this is still a little bit broken, as it might be important to create
    # sockets in the correct order to not try creating a connect socket for a simulator that doesnt support it
    def supported_socket_types(self) -> set[inst_base.SockType]:
        return {inst_base.SockType.LISTEN, inst_base.SockType.CONNECT}

    # Sockets to be cleaned up: always the CONNECTING sockets
    # pylint: disable=unused-argument
    def sockets_cleanup(self, inst: inst_base.Instantiation) -> list[inst_base.Socket]:
        return self._get_all_sockets_by_type(
            inst=inst, sock_type=inst_base.SockType.LISTEN
        )

    # sockets to wait for indicating the simulator is ready
    # pylint: disable=unused-argument
    def sockets_wait(self, inst: inst_base.Instantiation) -> list[inst_base.Socket]:
        return self._get_all_sockets_by_type(
            inst=inst, sock_type=inst_base.SockType.LISTEN
        )

    def start_delay(self) -> int:
        return 5

    def wait_terminate(self) -> bool:
        return False

    def supports_checkpointing(self) -> bool:
        return False


class Simulation(utils_base.IdObj):
    """
    Base class for all simulation experiments.

    Contains the simulators to be run and experiment-wide parameters.
    """

    def __init__(self, name: str) -> None:
        super().__init__()
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
        self.metadata: dict[str, tp.Any] = {}

        self._sys_sim_map: dict[sys_conf.Component, Simulator] = {}
        """System component and its simulator pairs"""

        self._chan_map: dict[sys_conf.Channel, sim_chan.Channel] = {}
        """Channel spec and its instanciation"""

    def add_spec_sim_map(self, sys: sys_conf.Component, sim: Simulator):
        """Add a mapping from specification to simulation instance"""
        if sys in self._sys_sim_map:
            raise Exception("system component is already mapped by simulator")
        self._sys_sim_map[sys] = sim

    def is_channel_instantiated(self, chan: Channel) -> bool:
        return chan in self._chan_map

    def retrieve_or_create_channel(self, chan: sys_conf.Channel) -> Channel:
        if self.is_channel_instantiated(chan):
            return self._chan_map[chan]

        channel = Channel(self, chan)
        self._chan_map[chan] = channel
        return channel

    def all_simulators(self) -> set[Simulator]:
        """Returns all simulators defined to run in this experiment."""
        simulators = set(map(lambda kv: kv[1], self._sys_sim_map.items()))
        return simulators

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
        if comp not in self._sys_sim_map:
            raise Exception("Simulator Not Found")
        return self._sys_sim_map[comp]

    # TODO: FIXME
    def enable_checkpointing_if_supported() -> None:
        raise Exception("not implemented")

    # TODO: FIXME
    def is_checkpointing_enabled(self) -> bool:
        raise Exception("not implemented")
