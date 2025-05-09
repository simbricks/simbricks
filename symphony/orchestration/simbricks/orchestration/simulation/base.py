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
import typing_extensions as tpe
import simbricks.orchestration.system as sys_conf
import simbricks.orchestration.instantiation.base as inst_base
import simbricks.orchestration.instantiation.socket as inst_socket
import simbricks.orchestration.simulation.channel as sim_chan
import simbricks.utils.base as utils_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.simulation import (
        Channel,
        base as sim_base,
    )


class Simulator(utils_base.IdObj, abc.ABC):
    """Base class for all simulators."""

    def __init__(
        self,
        simulation: sim_base.Simulation,
        executable: str,
        name: str = "",
    ) -> None:
        super().__init__()
        self.name: str = name
        self._executable: str = executable
        self._simulation: sim_base.Simulation = simulation
        self._components: set[sys_conf.Component] = set()
        self._wait: bool = False
        self._start_tick: int = 0
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
        return self.filter_components_by_pred(pred=lambda comp: isinstance(comp, ty), ty=ty)

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
                if app.wait:
                    return True
        return False

    @wait_terminate.setter
    def wait_terminate(self, wait: bool):
        self._wait = wait

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["name"] = self.name
        json_obj["executable"] = self._executable
        json_obj["simulation"] = self._simulation.id()

        components_json = []
        for comp in self._components:
            components_json.append(comp.id())
        json_obj["components"] = components_json

        json_obj["wait"] = self._wait
        json_obj["start_tick"] = self._start_tick
        json_obj["extra_args"] = self._extra_args
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: Simulation, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(json_obj)
        instance.name = utils_base.get_json_attr_top(json_obj, "name")
        instance._executable = utils_base.get_json_attr_top(json_obj, "executable")

        sim_id = int(utils_base.get_json_attr_top(json_obj, "simulation"))
        assert sim_id == simulation.id()
        instance._simulation = simulation

        instance._components = set()
        components_json = utils_base.get_json_attr_top(json_obj, "components")
        for comp_id in components_json:
            component = simulation.system.get_comp(comp_id)
            Simulator.add(instance, component)
            # instance.add(component)

        instance._wait = bool(utils_base.get_json_attr_top(json_obj, "wait"))
        instance._start_tick = int(utils_base.get_json_attr_top(json_obj, "start_tick"))
        instance._extra_args = utils_base.get_json_attr_top_or_none(json_obj, "extra_args")

        return instance

    @staticmethod
    def filter_sockets(
        sockets: list[inst_socket.Socket],
        filter_type: inst_socket.SockType = inst_socket.SockType.LISTEN,
    ) -> list[inst_socket.Socket]:
        res = list(filter(lambda sock: sock._type == filter_type, sockets))
        return res

    @staticmethod
    def split_sockets_by_type(
        sockets: list[inst_socket.Socket],
    ) -> tuple[list[inst_socket.Socket], list[inst_socket.Socket]]:
        listen = Simulator.filter_sockets(sockets=sockets, filter_type=inst_socket.SockType.LISTEN)
        connect = Simulator.filter_sockets(
            sockets=sockets, filter_type=inst_socket.SockType.CONNECT
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
                min(sync_period, channel.sync_period) if sync_period else channel.sync_period
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

    def get_parameters_url(
        self,
        inst: inst_base.Instantiation,
        socket: inst_socket.Socket,
        channel: sim_chan.Channel | None = None,
        sync: bool | None = None,
        latency: int | None = None,
        sync_period: int | None = None,
    ) -> str:
        if not channel and (sync == None or latency == None or sync_period == None):
            raise ValueError(
                "Cannot generate parameters url if channel and at least one of sync, "
                "latency, sync_period are None"
            )
        if channel:
            if not sync:
                sync = channel._synchronized
            if not latency:
                latency = channel.sys_channel.latency
            if not sync_period:
                sync_period = channel.sync_period

        sync_str = "true" if sync else "false"

        if socket._type == inst_socket.SockType.CONNECT:
            return (
                f"connect:{socket._path}:sync={sync_str}:latency={latency}"
                f":sync_interval={sync_period}"
            )
        else:
            return (
                f"listen:{socket._path}:{inst.env.get_simulator_shm_pool_path(self)}:sync={sync_str}"
                f":latency={latency}:sync_interval={sync_period}"
            )

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
        if chan.a.component in self._components and chan.b.component in self._components:
            return False
        return True

    def _get_socks_by_comp(
        self, inst: inst_base.Instantiation, comp: sys_conf.Component
    ) -> list[inst_socket.Socket]:
        if comp not in self._components:
            raise Exception("comp must be a simulators component")
        sockets = []
        for interface in comp.interfaces():
            socket = inst.get_socket(interface=interface)
            if socket is not None:
                sockets.append(socket)
        return sockets

    def _get_socks_by_all_comp(self, inst: inst_base.Instantiation) -> list[inst_socket.Socket]:
        sockets = []
        for comp in self._components:
            sockets.extend(self._get_socks_by_comp(inst=inst, comp=comp))
        return sockets

    def _get_all_sockets_by_type(
        self, inst: inst_base.Instantiation, sock_type: inst_socket.SockType
    ) -> list[inst_socket.Socket]:
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

    @staticmethod
    def filter_channels_by_sys_type(channels: list[sim_chan.Channel], ty: type[T]) -> list[T]:
        filtered = list(filter(lambda chan: isinstance(chan.sys_channel, ty), channels))
        return filtered

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
    def supported_socket_types(self, interface: sys_conf.Interface) -> set[inst_socket.SockType]:
        return set()

    # Sockets to be cleaned up: always the CONNECTING sockets
    # pylint: disable=unused-argument
    def sockets_cleanup(self, inst: inst_base.Instantiation) -> list[inst_socket.Socket]:
        return self._get_all_sockets_by_type(inst=inst, sock_type=inst_socket.SockType.LISTEN)

    # sockets to wait for indicating the simulator is ready
    # pylint: disable=unused-argument
    def sockets_wait(self, inst: inst_base.Instantiation) -> list[inst_socket.Socket]:
        return self._get_all_sockets_by_type(inst=inst, sock_type=inst_socket.SockType.LISTEN)

    def start_delay(self) -> int:
        return 5

    def supports_checkpointing(self) -> bool:
        return False

    async def prepare(self, inst: inst_base.Instantiation) -> None:
        promises = [comp.prepare(inst=inst) for comp in self._components]
        await asyncio.gather(*promises)

    def __repr__(self) -> str:
        return f"{str(self.__class__)}({self.full_name()})"


class DummySimulator(Simulator):

    def __init__(
        self,
        simulation: sim_base.Simulation,
        executable: str,
        name: str = "",
    ) -> None:
        super().__init__(simulation, executable, name)
        self._is_dummy = True

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        raise Exception("DummySimulator does not implement run_cmd")

    def supported_socket_types(self, interface: sys_conf.Interface) -> set[inst_socket.SockType]:
        raise Exception("DummySimulator does not implement supported_socket_types")

    @classmethod
    def fromJSON(cls, simulation: Simulation, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(simulation, json_obj)
        instance._is_dummy = True
        return instance


class Simulation(utils_base.IdObj):
    """
    Base class for all simulation experiments.

    Contains the simulators to be run and experiment-wide parameters.
    """

    def __init__(self, name: str, system: sys_conf.System) -> None:
        super().__init__()
        self.name = name
        """
        This experiment's name.

        Can be used to run only a selection of experiments.
        """
        self.system: sys_conf.System = system
        self.timeout: int | None = None
        """Timeout for experiment in seconds."""
        self.metadata: dict[str, tp.Any] = {}

        self._sys_sim_map: dict[sys_conf.Component, Simulator] = {}
        """System component and its simulator pairs"""
        self._sim_list: list[Simulator] = []
        """Channel spec and its instanciation"""

        self._chan_map: dict[sys_conf.Channel, sim_chan.Channel] = {}
        """Channel spec and its instanciation"""

        self._parameters: dict[tp.Any, tp.Any] = {}

    def toJSON(self) -> dict:
        """
        Serializes a Simulation.

        Note: The sys_sim_map is not serialized as the sim_list stores the required information implicitly as Simulators,
              when serialized store a list of their corresponding components.
        """
        json_obj = super().toJSON()

        json_obj["name"] = self.name
        json_obj["metadata"] = self.metadata
        json_obj["system"] = self.system.id()
        json_obj["timeout"] = self.timeout

        simulators_json = []
        for sim in self._sim_list:
            utils_base.has_attribute(sim, "toJSON")
            simulators_json.append(sim.toJSON())

        json_obj["sim_list"] = simulators_json

        chan_map_json = []
        chan_json = []
        for (
            sys_chan,
            sim_chan,
        ) in self._chan_map.items():
            utils_base.has_attribute(sim_chan, "toJSON")
            chan_json = sim_chan.toJSON()
            chan_map_json.append([sys_chan.id(), chan_json])
            # chan_json.append(sim_chan.toJSON())

        json_obj["chan_map"] = chan_map_json
        # json_obj["simulation_channels"] = chan_json

        json_obj["parameters"] = utils_base.dict_to_json(self._parameters)

        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_conf.System, json_obj: dict, enforce_dummies: bool = False) -> tpe.Self:
        """
        Deserializes a Simulation.

        Note: The sys_sim_map is not deserialized as the map is restored when deserializing the the sim_list.
              This is possible as each Simulator stores when a list of their corresponding components when serialized.
        """

        instance = super().fromJSON(json_obj)
        instance.metadata = utils_base.get_json_attr_top(json_obj, "metadata")
        instance.name = utils_base.get_json_attr_top(json_obj, "name")
        system_id = int(utils_base.get_json_attr_top(json_obj, "system"))
        assert system_id == system.id()
        instance.system = system
        instance.timeout = utils_base.get_json_attr_top_or_none(json_obj, "timeout")

        instance._sim_list = []
        instance._sys_sim_map = {}
        simulators_json = utils_base.get_json_attr_top(json_obj, "sim_list")
        for sim_json in simulators_json:
            sim_class = utils_base.get_cls_by_json(sim_json, False)

            sim = None
            if enforce_dummies or sim_class is None:
                sim = DummySimulator.fromJSON(instance, sim_json)
            else:
                utils_base.has_attribute(sim_class, "fromJSON")
                sim = sim_class.fromJSON(instance, sim_json)

            assert sim
            instance._sim_list.append(sim)

        instance._chan_map = {}
        chan_map_json = utils_base.get_json_attr_top(json_obj, "chan_map")
        for sys_id, chan_json in chan_map_json:
            chan_class = utils_base.get_cls_by_json(chan_json)
            utils_base.has_attribute(chan_class, "fromJSON")
            sim_chan = chan_class.fromJSON(instance, chan_json)
            sys_chan = instance.system.get_chan(sys_id)
            instance.update_channel_mapping(sys_chan=sys_chan, sim_chan=sim_chan)

        instance._parameters = utils_base.json_to_dict(
            utils_base.get_json_attr_top(json_obj, "parameters")
        )

        return instance

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

    def update_channel_mapping(
        self, sys_chan: sys_conf.Channel, sim_chan: sim_chan.Channel
    ) -> None:
        if self.is_channel_instantiated(sys_chan):
            raise Exception(
                f"channel {sys_chan} is already mapped. Cannot insert mapping {sys_chan.id()} -> {sim_chan.id()}"
            )
        self._chan_map[sys_chan] = sim_chan

    def retrieve_or_create_channel(self, chan: sys_conf.Channel) -> sim_chan.Channel:
        if self.is_channel_instantiated(chan):
            return self._chan_map[chan]

        channel = sim_chan.Channel(chan)
        self.update_channel_mapping(sys_chan=chan, sim_chan=channel)
        return channel

    def get_channel(self, chan: sys_conf.Channel) -> sim_chan.Channel:
        if not self.is_channel_instantiated(chan):
            raise RuntimeError(f"Channel {chan} is not instantiated")
        return self._chan_map[chan]

    def get_channel_by_id(self, id: int) -> sim_chan.Channel:
        # TODO: avoid iterating over all values of the _chan_map
        for channel in self._chan_map.values():
            if channel.id() == id:
                return channel
        # TODO: use more specific exception
        raise RuntimeError(f"there is no channel with id {id}")

    def all_simulators(self) -> list[Simulator]:
        return self._sim_list

    def get_simulator(self, id: int) -> Simulator:
        # TODO: avoid iterating over the list of simulators
        for sim in self._sim_list:
            if sim.id() == id:
                return sim
        # TODO: use more specific exception
        raise RuntimeError("could not find simulator with id {id}")

    def get_all_channels(self, lazy: bool = False) -> list[Channel]:
        if lazy:
            return list(self._chan_map.values())

        all_channels = []
        for sim in self.all_simulators():
            channels = sim.get_channels()
            all_channels.extend(channels)
        return all_channels

    def enable_synchronization(
        self, amount: int | None = None, ratio: utils_base.Time | None = None
    ) -> None:
        for chan in self.get_all_channels():
            chan._synchronized = True
            if amount and ratio:
                chan.set_sync_period(amount=amount, ratio=ratio)

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
        for sim in inst.assigned_fragment.all_simulators():
            promises.append(sim.prepare(inst=inst))
        await asyncio.gather(*promises)

    def any_supports_checkpointing(self) -> bool:
        if len(list(filter(lambda sim: sim.supports_checkpointing(), self._sim_list))) > 0:
            return True
        return False
