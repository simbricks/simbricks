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
        self._socket_tracker: set[tuple[simulation.channel.Channel, SockType]] = set()

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

    def _interface_to_sock_path(self, interface: system.base.Interface) -> str:
        basepath = pathlib.Path(self._env._workdir)
        match interface:
            case PCIeHostInterface() | PCIeDeviceInterface():
                return f"{self._env._shm_base}/shm.pci/{interface.component.name}.{interface._id}"
            case MemDeviceInterface() | MemHostInterface():
                return f"{self._env._shm_base}/shm.mem/{interface.component.name}.{interface._id}"
            case EthInterface():
                return f"{self._env._shm_base}/shm.eth/{interface.component.name}.{interface._id}"
            case _:
                raise Exception("cannot create socket path for given interface type")

    def get_socket(self, interface: system.base.Interface) -> Socket:

        # TODO: use self._socket_tracker to determine socket type that is needed
        sock_type = SockType.LISTEN

        # TODO: generate socket path
        sock_path = self._interface_to_sock_path(interface=interface)

        return Socket(sock_path, sock_type)

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
