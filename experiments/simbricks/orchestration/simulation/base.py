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
import asyncio
import typing as tp
import simbricks.orchestration.system as sys_conf
import simbricks.orchestration.instantiation.base as inst_base
import simbricks.orchestration.simulation.channel as sim_chan
import simbricks.orchestration.utils.base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.simulation import (
        Channel,
        base as sim_base,
    )


class Simulator(utils_base.IdObj):
    """Base class for all simulators."""

    def __init__(
        self,
        simulation: sim_base.Simulation,
        executable: str,
        name: str = "",
    ) -> None:
        super().__init__()
        self.name: str = name
        self._executable = executable
        self._simulation: sim_base.Simulation = simulation
        self._components: set[sys_conf.Component] = set()
        self._wait: bool = False
        self._start_tick = 0
        """The timestamp at which to start the simulation. This is useful when
        the simulator is only attached at a later point in time and needs to
        synchronize with connected simulators. For example, this could be used
        when taking checkpoints to only attach certain simulators after the
        checkpoint has been taken."""
        self._extra_args: str | None = None
        simulation.add_sim(self)

    T = tp.TypeVar("T")

    def filter_components_by_pred(
        self,
        pred: tp.Callable[[sys_conf.Component], bool],
        ty: type[T] = sys_conf.Component,
    ) -> list[T]:
        return list(filter(pred, self._components))

    def filter_components_by_type(self, ty: type[T]) -> list[T]:
        return self.filter_components_by_pred(
            pred=lambda comp: isinstance(comp, ty), ty=ty
        )

    @property
    def extra_args(self) -> str:
        return self._extra_args

    @extra_args.setter
    def extra_args(self, extra_args: str):
        self._extra_args = extra_args

    @property
    def wait_terminate(self) -> bool:
        if self._wait:
            return True
        host_comps = self.filter_components_by_type(ty=sys_conf.Host)
        for host in host_comps:
            for app in host.applications:
                if not isinstance(app, sys_conf.BaseLinuxApplication):
                    continue
                lin_app: sys_conf.BaseLinuxApplication = app
                if lin_app.wait:
                    return True
        return False

    @wait_terminate.setter
    def wait_terminate(self, wait: bool):
        self._wait = wait

    @staticmethod
    def filter_sockets(
        sockets: list[inst_base.Socket],
        filter_type: inst_base.SockType = inst_base.SockType.LISTEN,
    ) -> list[inst_base.Socket]:
        res = list(filter(lambda sock: sock._type == filter_type, sockets))
        return res

    @staticmethod
    def split_sockets_by_type(
        sockets: list[inst_base.Socket],
    ) -> tuple[list[inst_base.Socket], list[inst_base.Socket]]:
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
        latency = None
        sync_period = None
        run_sync = False
        for channel in channels:
            sync_period = (
                min(sync_period, channel.sync_period)
                if sync_period
                else channel.sync_period
            )
            run_sync = run_sync or channel._synchronized
            latency = (
                max(latency, channel.sys_channel.latency)
                if latency
                else channel.sys_channel.latency
            )
        if latency is None or sync_period is None:
            raise Exception("could not determine eth_latency and sync_period")
        return latency, sync_period, run_sync

    def components(self) -> set[sys_conf.Component]:
        return self._components

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

    def add(self, comp: sys_conf.Component) -> None:
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

    def _get_socks_by_comp(
        self, inst: inst_base.Instantiation, comp: sys_conf.Component
    ) -> list[inst_base.Socket]:
        if comp not in self._components:
            raise Exception("comp must be a simulators component")
        sockets = []
        for interface in comp.interfaces():
            socket = inst.get_socket(interface=interface)
            if socket:
                sockets.append(socket)
        return sockets

    def _get_socks_by_all_comp(
        self, inst: inst_base.Instantiation
    ) -> list[inst_base.Socket]:
        sockets = []
        for comp in self._components:
            sockets.extend(self._get_socks_by_comp(inst=inst, comp=comp))
        return sockets

    def _get_all_sockets_by_type(
        self, inst: inst_base.Instantiation, sock_type: inst_base.SockType
    ) -> list[inst_base.Socket]:
        sockets = self._get_socks_by_all_comp(inst=inst)
        sockets = Simulator.filter_sockets(sockets=sockets, filter_type=sock_type)
        return sockets

    def _get_channel(self, chan: sys_conf.Channel) -> sim_chan.Channel | None:
        if self._chan_needs_instance(chan):
            return self._simulation.retrieve_or_create_channel(chan=chan)
        return None

    def get_channels(self) -> list[sim_chan.Channel]:
        channels = []
        for comp_spec in self._components:
            comp_sys_channels = comp_spec.channels()
            for chan in comp_sys_channels:
                channel = self._get_channel(chan=chan)
                if channel is None:
                    continue
                channels.append(channel)
        return channels

    # pylint: disable=unused-argument
    @abc.abstractmethod
    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        """Command to execute this simulator."""
        raise Exception("must be implemented in sub-class")

    def checkpoint_commands(self) -> list[str]:
        return []

    def cleanup_commands(self) -> list[str]:
        return []

    @abc.abstractmethod
    def supported_socket_types(
        self, interface: sys_conf.Interface
    ) -> set[inst_base.SockType]:
        return []

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

    def supports_checkpointing(self) -> bool:
        return False

    async def prepare(self, inst: inst_base.Instantiation) -> None:
        promises = [comp.prepare(inst=inst) for comp in self._components]
        await asyncio.gather(*promises)


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

        self._sim_list: list[Simulator] = []
        """Channel spec and its instanciation"""

    def add_sim(self, sim: Simulator):
        if sim in self._sim_list:
            raise Exception("Simulaotr is already added")
        self._sim_list.append(sim)

    def add_spec_sim_map(self, sys: sys_conf.Component, sim: Simulator):
        """Add a mapping from specification to simulation instance"""
        if sys in self._sys_sim_map:
            raise Exception("system component is already mapped by simulator")
        self._sys_sim_map[sys] = sim

    def is_channel_instantiated(self, chan: sys_conf.Channel) -> bool:
        return chan in self._chan_map

    def retrieve_or_create_channel(self, chan: sys_conf.Channel) -> sim_chan.Channel:
        if self.is_channel_instantiated(chan):
            return self._chan_map[chan]

        channel = sim_chan.Channel(chan)
        self._chan_map[chan] = channel
        return channel

    def all_simulators(self) -> list[Simulator]:
        return self._sim_list

    def get_all_channels(self, lazy: bool = False) -> list[Channel]:
        if lazy:
            return list(self._chan_map.values())

        all_channels = []
        for sim in self.all_simulators():
            channels = sim.get_channels()
            all_channels.extend(channels)
        return all_channels

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
        utils_base.has_expected_type(comp, sys_conf.Component)
        if comp not in self._sys_sim_map:
            raise Exception(f"Simulator not found for component: {comp}")
        return self._sys_sim_map[comp]

    async def prepare(self, inst: inst_base.Instantiation) -> None:
        promises = []
        for sim in self._sim_list:
            promises.append(sim.prepare(inst=inst))
        await asyncio.gather(*promises)

    # TODO: FIXME
    def enable_checkpointing_if_supported() -> None:
        raise Exception("not implemented")

    # TODO: FIXME
    def is_checkpointing_enabled(self) -> bool:
        raise Exception("not implemented")
