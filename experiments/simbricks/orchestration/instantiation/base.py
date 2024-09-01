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

from simbricks.orchestration import simulation
from simbricks.orchestration import system
import enum
import pathlib


class SockType(enum.Enum):
    LISTEN = enum.auto()
    CONNECT = enum.auto()


class Socket:

    def __init__(self, path: str = "", ty: SockType = SockType.LISTEN):
        self._path = path
        self._type = ty


class InstantiationEnvironment:

    def __init__(
        self,
        repo_path: str = pathlib.Path(__file__).parents[3].resolve(),
        workdir: str = pathlib.Path(),
        cpdir: str = pathlib.Path(),
        shm_base: str = pathlib.Path(),
    ):
        # TODO: add more parameters that wont change during instantiation
        self._repodir: str = pathlib.Path(repo_path).absolute()
        self._workdir: str = pathlib.Path(workdir).absolute()
        self._cpdir: str = pathlib.Path(cpdir).absolute()
        self._shm_base = pathlib.Path(workdir).joinpath(shm_base).absolute()


class Instantiation:

    def __init__(
        self, simulation, env: InstantiationEnvironment = InstantiationEnvironment()
    ):
        self._simulation = simulation
        self._env: InstantiationEnvironment = env
        self._socket_tracker: dict[simulation.channel.Channel, Socket] = {}

    @staticmethod
    def is_absolute_exists(path: str) -> bool:
        path = pathlib.Path(path)
        return path.is_absolute() and path.is_file()

    #    def dev_pci_path(self, sim) -> str:
    #        return f"{self.workdir}/dev.pci.{sim.name}"
    #
    #    def dev_mem_path(self, sim: "simulators.Simulator") -> str:
    #        return f"{self.workdir}/dev.mem.{sim.name}"
    #
    #    def nic_eth_path(self, sim: "simulators.Simulator") -> str:
    #        return f"{self.workdir}/nic.eth.{sim.name}"
    #
    #    def dev_shm_path(self, sim: "simulators.Simulator") -> str:
    #        return f"{self.shm_base}/dev.shm.{sim.name}"
    #
    #    def n2n_eth_path(
    #        self, sim_l: "simulators.Simulator", sim_c: "simulators.Simulator", suffix=""
    #    ) -> str:
    #        return f"{self.workdir}/n2n.eth.{sim_l.name}.{sim_c.name}.{suffix}"
    #
    #    def net2host_eth_path(self, sim_n, sim_h) -> str:
    #        return f"{self.workdir}/n2h.eth.{sim_n.name}.{sim_h.name}"
    #
    #    def net2host_shm_path(
    #        self, sim_n: "simulators.Simulator", sim_h: "simulators.Simulator"
    #    ) -> str:
    #        return f"{self.workdir}/n2h.shm.{sim_n.name}.{sim_h.name}"
    #
    #    def proxy_shm_path(self, sim: "simulators.Simulator") -> str:
    #        return f"{self.shm_base}/proxy.shm.{sim.name}"

    def _get_chan_by_interface(
        self, interface: system.base.Interface
    ) -> simulation.channel.Channel:
        if not interface.is_connected():
            raise Exception(
                "cannot determine channel by interface, interface isn't connecteds"
            )
        channel = interface.channel
        return channel

    def _get_socket_by_channel(
        self, channel: simualtion.channel.Channel
    ) -> Socket | None:
        if not channel in self._socket_tracker:
            return None
        return self._socket_tracker[channel]

    def _updated_tracker_mapping(
        self, interface: system.base.Interface, socket: Socket
    ) -> None:
        channel = self._get_chan_by_interface(interface=interface)
        if channel in self._socket_tracker:
            raise Exception(
                "cannot update socket tracker mapping, channel is already mapped"
            )
        self._socket_tracker[channel] = socket

    def _get_socket_by_interface(self, interface: system.base.Interface) -> str | None:
        # TODO
        pass

    def _interface_to_sock_path(self, interface: system.base.Interface) -> str:
        basepath = pathlib.Path(self._env._workdir)

        channel = self._get_chan_by_interface(interface=interface)
        sys_channel = channel.sys_channel
        queue_ident = f"{sys_channel.a._id}.{sys_channel._id}.{sys_channel.b._id}"

        queue_type = None
        match interface:
            case PCIeHostInterface() | PCIeDeviceInterface():
                queue_type = "shm.pci"
            case MemDeviceInterface() | MemHostInterface():
                queue_type = "shm.mem"
            case EthInterface():
                queue_type = "shm.eth"
            case _:
                raise Exception("cannot create socket path for given interface type")

        assert queue_type is not None
        return f"{self._env._shm_base}/{queue_type}/{queue_ident}"

    def _create_opposing_socket(self, socket: Socket) -> Socket:
        new_ty = (
            SockType.LISTEN if socket._type == SockType.CONNECT else SockType.LISTEN
        )
        new_path = socket._path
        new_socket = Socket(path=new_path, ty=new_ty)
        return new_socket

    def get_socket(self, interface: system.base.Interface) -> Socket:
        # The other side already created a socket, we just create the opposing
        # side (i.e. connect or listening depending on the already created type)
        # and return
        socket = self._get_socket_by_interface(interface=interface)
        if socket is not None:
            new_socket = self._create_opposing_socket(socket=socket)

        # neither connecting nor listening side already created a socket, thus we
        # create a completely new 'CONNECT' socket
        sock_type = SockType.CONNECT
        # create the socket path
        sock_path = self._interface_to_sock_path(interface=interface)
        new_socket = Socket(path=sock_path, ty=sock_type)

        # update the socket tracker mapping for other side
        self._updated_tracker_mapping(interface=interface, socket=new_socket)

        return new_socket

    # TODO: add more methods constructing paths as required by methods in simulators or image handling classes

    def join_repo_base(self, relative_path: str) -> str:
        path = pathlib.Path(self._env._repodir)
        path.joinpath(relative_path)
        if not path.exists():
            raise Exception(f"couldn't join {self._env._repodir} and {relative_path}")
        return path.absolute()

    def hd_path(self, hd_name_or_path: str) -> str:
        if Instantiation.is_absolute_exists(hd_name_or_path):
            return hd_name_or_path

        path = pathlib.Path(
            f"{self._env._repodir}/images/output-{hd_name_or_path}/{hd_name_or_path}"
        )

        return path.absolute()

    def dynamic_img_path(self, format: str) -> str:
        # TODO
        return ""
