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

import abc
import shlex
import typing

from simbricks.orchestration.helpers import exceptions
from simbricks.orchestration.instantiation import socket as inst_socket
from simbricks.utils import base as utils_base
from simbricks.utils import file as utils_file

if typing.TYPE_CHECKING:
    import simbricks.orchestration.system.base as sys_base
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.instantiation import fragment as inst_fragment
    from simbricks.orchestration.simulation import base as sim_base


class Proxy(utils_base.IdObj, abc.ABC):

    def __init__(self):
        super().__init__()
        self._interfaces: list[sys_base.Interface]
        """
        The interfaces this proxy handles.
        
        Order is important here because proxies forward messages for SimBricks
        sockets in the order these sockets are passed on the command-line. So
        for two connecting proxies executing on separate runners, this order
        must be the same.
        """
        self._connection_mode: inst_socket.SockType | None = None
        self._ip: str | None = None
        """If this is a connecting proxy, the IP to connect to."""
        self._port: int | None = None
        """If this is a connecting proxy, the port to connect to."""
        self._ready_file: str | None = None
        """Used to syncyhronize access to port_ip_file. If ready_file exists, we know that we can
        safely ready the contents of port_ip_file."""
        self._listen_info_file: str | None = None
        """Path to file that proxy creates, which contains the port and IP it is listening to."""

    def toJSON(self) -> dict:
        json_obj = super().toJSON()

        json_obj["interfaces"] = list(map(lambda interface: interface.id(), self._interfaces))
        json_obj["connection_mode"] = self._connection_mode.value if self._connection_mode else None
        json_obj["ip"] = self._ip
        json_obj["port"] = self._port
        # TODO: do we actually need to serialize this?
        json_obj["ready_file"] = self._ready_file
        # TODO: do we actually need to serialize this?
        json_obj["listen_info_file"] = self._listen_info_file

        return json_obj

    @classmethod
    def fromJSON(cls, json_obj: dict, simulation: sim_base.Simulation) -> Proxy:
        instance = super().fromJSON(json_obj)

        interface_ids = utils_base.get_json_attr_top(json_obj, "interfaces")
        instance._interfaces = []
        for interface_id in interface_ids:
            interface = simulation.system.get_inf(interface_id)
            instance._interfaces.append(interface)

        connection_mode = utils_base.get_json_attr_top(json_obj, "connection_mode")
        if connection_mode is not None:
            instance._connection_mode = inst_socket.SockType(connection_mode)
        else:
            instance._connection_mode = None
        instance._ip = utils_base.get_json_attr_top(json_obj, "ip")
        instance._port = utils_base.get_json_attr_top(json_obj, "port")
        instance._ready_file = utils_base.get_json_attr_top(json_obj, "ready_file")
        instance._listen_info_file = utils_base.get_json_attr_top(json_obj, "listen_info_file")

        return instance

    @property
    def name(self) -> str:
        return f"proxy_{self.id()}"

    @property
    def interfaces(self) -> list[sys_base.Interface]:
        return self._interfaces

    @abc.abstractmethod
    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        pass

    def sockets_wait(self, inst: inst_base.Instantiation) -> set[inst_socket.Socket]:
        wait_sockets = []
        for iface in self._interfaces:
            socket = inst.get_socket(iface)
            if inst.get_interface_socktype == inst_socket.SockType.LISTEN:
                wait_sockets.append(socket)
        return wait_sockets

    async def wait_ready(self) -> None:
        if self._ready_file is None:
            raise RuntimeError("Proxy does not specify a ready_file")
        await utils_file.await_file(self._ready_file)

    async def read_listening_info(self) -> None:
        if self._listen_info_file is None:
            raise RuntimeError("Proxy does not specify a listen_info_file")
        await self.wait_ready()
        with open(self._listen_info_file, mode="r", encoding="utf-8") as file:
            lines = file.readlines()
        self._port = int(lines[0])

    def __repr__(self):
        return f"{self.name}"


class DummyProxy(Proxy):

    async def read_listening_info(self) -> None:
        pass

    async def run_cmd(self, inst: inst_base.Instantiation) -> str:
        raise NotImplementedError("function run_cmd() should not be called for DummyProxy")


class TCPProxy(Proxy):

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        proxy_bin = inst.env.repo_base("dist/sockets/net_sockets")
        cmd_args = [proxy_bin]

        if self._connection_mode == inst_socket.SockType.LISTEN:
            cmd_args.append("-l")

        shm_path = inst.env.shm_base(f"proxy-shm-pool-{self.id()}")
        cmd_args.append("-s")
        cmd_args.append(shm_path)
        # TODO: allow to set shm size

        for interface in self._interfaces:
            if inst.get_interface_socktype(interface) == inst_socket.SockType.CONNECT:
                cmd_args.append("-L")
            else:
                cmd_args.append("-C")
            cmd_args.append(inst.get_socket(interface)._path)

        if self._ip is None or self._port is None:
            raise RuntimeError("Ip and port of proxy must be not None")
        cmd_args.append(f"{self._ip}")
        cmd_args.append(f"{self._port}")

        self._listen_info_file = inst.env.tmp_simulation_files(
            f"proxy-listen-info-file-{self.id()}"
        )
        cmd_args.append(self._listen_info_file)
        self._ready_file = inst.env.tmp_simulation_files(f"proxy-ready-file-{self.id()}")
        cmd_args.append(self._ready_file)

        return shlex.join(cmd_args)


class RDMAProxy(Proxy):
    def __init__(self, ready_file, port_ip_file):
        super().__init__(ready_file, port_ip_file)
        # TODO: Implement this
        raise NotImplementedError("TODO: Implement this")


class ProxyPair(utils_base.IdObj):

    def __init__(
        self,
        instantiation: inst_base.Instantiation,
        fragment_a: inst_fragment.Fragment,
        fragment_b: inst_fragment.Fragment,
        proxy_a: Proxy,
        proxy_b: Proxy,
    ) -> None:
        self._inst: inst_base.Instantiation = instantiation
        self._channels: set[sim_base.Channel] = set()
        self.fragment_a: inst_fragment.Fragment = fragment_a
        self.fragment_b: inst_fragment.Fragment = fragment_b
        self.proxy_a: Proxy = proxy_a
        self.proxy_b: Proxy = proxy_b
        assert proxy_a in fragment_a.all_proxies()
        assert proxy_b in fragment_b.all_proxies()

    def toJSON(self) -> dict:
        json_obj = super().toJSON()

        json_obj["instantiation"] = self._inst.id()
        json_obj["channels"] = list(map(lambda chan: chan.id(), self._channels))
        json_obj["fragment_a"] = self.fragment_a.id()
        json_obj["fragment_b"] = self.fragment_b.id()
        json_obj["proxy_a"] = self.proxy_a.id()
        json_obj["proxy_b"] = self.proxy_b.id()

        return json_obj

    @classmethod
    def fromJSON(cls, json_obj: dict, instantiation: inst_base.Instantiation) -> ProxyPair:
        instance = super().fromJSON(json_obj)

        instantiation_id = utils_base.get_json_attr_top(json_obj, "instantiation")
        assert instantiation.id() == instantiation_id
        instance._inst = instantiation

        channel_ids = utils_base.get_json_attr_top(json_obj, "channels")
        instance._channels = set()
        for channel_id in channel_ids:
            channel = instantiation.simulation.get_channel_by_id(channel_id)
            instance._channels.add(channel)

        fragment_a_id = utils_base.get_json_attr_top(json_obj, "fragment_a")
        instance.fragment_a = instantiation.get_fragment(fragment_a_id)
        fragment_b_id = utils_base.get_json_attr_top(json_obj, "fragment_b")
        instance.fragment_b = instantiation.get_fragment(fragment_b_id)

        proxy_a_id = utils_base.get_json_attr_top(json_obj, "proxy_a")
        instance.proxy_a = instance.fragment_a.get_proxy_by_id(proxy_a_id)
        proxy_b_id = utils_base.get_json_attr_top(json_obj, "proxy_b")
        instance.proxy_b = instance.fragment_b.get_proxy_by_id(proxy_b_id)

        return instance

    def assign_sim_channel(self, channel: sys_base.Channel) -> None:
        self._channels.add(channel)
        # Goal is to assign the two interfaces of channel to their corresponding proxy
        iface_x, iface_y = channel.interfaces()
        sim_x = self._inst.find_sim_by_interface(iface_x)
        sim_y = self._inst.find_sim_by_interface(iface_y)
        if sim_x in self.fragment_a.all_simulators() and sim_y in self.fragment_b.all_simulators():
            self.proxy_a._interfaces.append(iface_x)
            self.proxy_b._interfaces.append(iface_y)
        elif (
            sim_y in self.fragment_a.all_simulators() and sim_x in self.fragment_b.all_simulators()
        ):
            self.proxy_a._interfaces.append(iface_y)
            self.proxy_b._interfaces.append(iface_x)
        else:
            raise exceptions.InstantiationConfigurationError(
                f"Cannot find the fragments that the simulators on both sides of the given channel belong to. Make sure the following simulators are correctly assigned to fragments before calling assign_sim_channel(): {sim_x} and {sim_y}"
            )
