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

import asyncio
import enum
import pathlib
import shutil
import typing
from simbricks.orchestration.utils import base as util_base
from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import pcie as sys_pcie
from simbricks.orchestration.system import mem as sys_mem
from simbricks.orchestration.system import eth as sys_eth
from simbricks.orchestration.system.host import base as sys_host
from simbricks.orchestration.system.host import disk_images
from simbricks.orchestration.runtime_new import command_executor

if typing.TYPE_CHECKING:
    from simbricks.orchestration.simulation import base as sim_base


class SockType(enum.Enum):
    LISTEN = enum.auto()
    CONNECT = enum.auto()


class Socket:

    def __init__(self, path: str = "", ty: SockType = SockType.LISTEN):
        self._path = path
        self._type = ty


class InstantiationEnvironment(util_base.IdObj):

    def __init__(
        self,
        repo_path: str = pathlib.Path(__file__).parents[3].resolve(),
        workdir: str = pathlib.Path().resolve(),
        cpdir: str = pathlib.Path().resolve(),
        create_cp: bool = False,
        restore_cp: bool = False,
        shm_base: str = pathlib.Path().resolve(),
        output_base: str = pathlib.Path().resolve(),
        tmp_simulation_files: str = pathlib.Path().resolve(),
        qemu_img_path: str | None = None,
        qemu_path: str | None = None,
    ):
        super().__init__()
        # TODO: add more parameters that wont change during instantiation
        self._repodir: str = pathlib.Path(repo_path).absolute()
        self._workdir: str = pathlib.Path(workdir).absolute()
        self._cpdir: str = pathlib.Path(cpdir).absolute()
        self._shm_base: str = pathlib.Path(self._workdir).joinpath(shm_base).absolute()
        self._output_base: str = (
            pathlib.Path(self._workdir).joinpath(output_base).absolute()
        )
        self._tmp_simulation_files: str = (
            pathlib.Path(self._workdir).joinpath(tmp_simulation_files).absolute()
        )
        self._create_cp: bool = create_cp
        self._restore_cp: bool = restore_cp

        self._qemu_img_path: str = (
            qemu_img_path
            if qemu_img_path
            else pathlib.Path(
                f"{self._repodir}/sims/external/qemu/build/qemu-img"
            ).resolve()
        )
        self._qemu_path: str = (
            qemu_path
            if qemu_path
            else pathlib.Path(
                f"{self._repodir}/sims/external/qemu/build/x86_64-softmmu/qemu-system-x86_64"
            ).resolve()
        )


class Instantiation(util_base.IdObj):

    def __init__(
        self,
        sim: sim_base.Simulation,
        env: InstantiationEnvironment = InstantiationEnvironment(),
    ):
        super().__init__()
        self._simulation: sim_base.Simulation = sim
        self._env: InstantiationEnvironment = env
        self._executor: command_executor.Executor | None = None
        self._socket_per_interface: dict[sys_base.Interface, Socket] = {}

    @staticmethod
    def is_absolute_exists(path: str) -> bool:
        path = pathlib.Path(path)
        return path.is_absolute() and path.is_file()

    @property
    def executor(self):
        if self._executor is None:
            raise Exception("you must set an executor")
        return self._executor

    @executor.setter
    def executor(self, executor: command_executor.Executor):
        self._executor = executor

    def restore_cp(self) -> bool:
        return self._env._restore_cp

    def qemu_img_path(self) -> str:
        return self._env._qemu_img_path

    def qemu_path(self) -> str:
        return self._env._qemu_path

    def _get_chan_by_interface(self, interface: sys_base.Interface) -> sys_base.Channel:
        if not interface.is_connected():
            raise Exception(
                "cannot determine channel by interface, interface isn't connecteds"
            )
        return interface.channel

    def _get_opposing_interface(
        self, interface: sys_base.Interface
    ) -> sys_base.Interface:
        channel = self._get_chan_by_interface(interface=interface)
        return channel.a if channel.a is not interface else channel.b

    def _updated_tracker_mapping(
        self, interface: sys_base.Interface, socket: Socket
    ) -> None:
        # update interface mapping
        if interface in self._socket_per_interface:
            raise Exception("an interface cannot be associated with two sockets")
        self._socket_per_interface[interface] = socket

    def _get_socket_by_interface(self, interface: sys_base.Interface) -> Socket | None:
        if interface not in self._socket_per_interface:
            return None
        return self._socket_per_interface[interface]

    def _get_opposing_socket_by_interface(
        self, interface: sys_base.Interface
    ) -> Socket | None:
        opposing_interface = self._get_opposing_interface(interface=interface)
        socket = self._get_socket_by_interface(interface=opposing_interface)
        return socket

    def _interface_to_sock_path(self, interface: sys_base.Interface) -> str:
        channel = self._get_chan_by_interface(interface=interface)
        queue_ident = f"{channel.a._id}.{channel._id}.{channel.b._id}"

        queue_type = None
        match interface:
            case sys_pcie.PCIeHostInterface() | sys_pcie.PCIeDeviceInterface():
                queue_type = "shm.pci"
            case sys_mem.MemDeviceInterface() | sys_mem.MemHostInterface():
                queue_type = "shm.mem"
            case sys_eth.EthInterface():
                queue_type = "shm.eth"
            case _:
                raise Exception("cannot create socket path for given interface type")

        assert queue_type is not None
        return self._join_paths(
            base=self._env._shm_base,
            relative_path=f"/{queue_type}/{queue_ident}",
            enforce_existence=False,
        )

    def _create_opposing_socket(
        self, socket: Socket, supported_sock_types: set[SockType] = set()
    ) -> Socket:
        new_ty = (
            SockType.LISTEN if socket._type == SockType.CONNECT else SockType.LISTEN
        )
        if new_ty not in supported_sock_types:
            raise Exception(
                f"cannot create opposing socket, as required type is not supported: required={new_ty}, supported={','.join(supported_sock_types)}"
            )
        new_path = socket._path
        new_socket = Socket(path=new_path, ty=new_ty)
        return new_socket

    def get_socket(
        self,
        interface: sys_base.Interface,
        supported_sock_types: set[SockType] = set(),
    ) -> Socket:
        # check if already a socket is associated with this interface
        socket = self._get_socket_by_interface(interface=interface)
        if socket is not None:
            return socket

        # Check if other side already created a socket, and create an opposing one
        socket = self._get_opposing_socket_by_interface(interface=interface)
        if socket is not None:
            new_socket = self._create_opposing_socket(
                socket=socket, supported_sock_types=supported_sock_types
            )
            self._updated_tracker_mapping(interface=interface, socket=new_socket)
            return new_socket

        # neither connecting nor listening side already created a socket, thus we
        # create a completely new 'CONNECT' socket
        if len(supported_sock_types) > 1 or (
            SockType.LISTEN not in supported_sock_types
            and SockType.CONNECT not in supported_sock_types
        ):
            raise Exception("cannot create a socket if no socket type is supported")
        sock_type = (
            SockType.CONNECT
            if SockType.CONNECT in supported_sock_types
            else SockType.LISTEN
        )
        sock_path = self._interface_to_sock_path(interface=interface)
        new_socket = Socket(path=sock_path, ty=sock_type)
        self._updated_tracker_mapping(interface=interface, socket=new_socket)
        return new_socket

    async def cleanup_sockets(
        self,
        sockets: list[Socket] = [],
    ) -> None:
        scs = []
        for sock in sockets:
            scs.append(asyncio.create_task(self.executor.rmtree(path=sock._path)))
        if len(scs) > 0:
            await asyncio.gather(*scs)

    async def wait_for_sockets(
        self,
        sockets: list[Socket] = [],
    ) -> None:
        wait_socks = list(map(lambda sock: sock._path, sockets))
        await self.executor.await_files(wait_socks, verbose=True)

    # TODO: add more methods constructing paths as required by methods in simulators or image handling classes

    def wrkdir(self) -> str:
        return pathlib.Path(self._env._workdir).absolute()

    def shm_base_dir(self) -> str:
        return pathlib.Path(self._env._shm_base).absolute()

    def create_cp(self) -> bool:
        return self._env._create_cp

    def cpdir(self) -> str:
        return pathlib.Path(self._env._cpdir).absolute()

    def wrkdir(self) -> str:
        return pathlib.Path(self._env._workdir).absolute()

    async def prepare(self) -> None:
        wrkdir = self.wrkdir()
        shutil.rmtree(wrkdir, ignore_errors=True)
        await self.executor.rmtree(wrkdir)

        shm_base = self.shm_base_dir()
        shutil.rmtree(shm_base, ignore_errors=True)
        await self.executor.rmtree(shm_base)

        cpdir = self.cpdir()
        if self.create_cp():
            shutil.rmtree(cpdir, ignore_errors=True)
            await self.executor.rmtree(cpdir)

        pathlib.Path(wrkdir).mkdir(parents=True, exist_ok=True)
        await self.executor.mkdir(wrkdir)

        pathlib.Path(cpdir).mkdir(parents=True, exist_ok=True)
        await self.executor.mkdir(cpdir)

        pathlib.Path(shm_base).mkdir(parents=True, exist_ok=True)
        await self.executor.mkdir(shm_base)

        await self._simulation.prepare(inst=self)

    def _join_paths(
        self, base: str = "", relative_path: str = "", enforce_existence=False
    ) -> str:
        path = pathlib.Path(base)
        joined = path.joinpath(relative_path)
        if not joined.exists() and enforce_existence:
            raise Exception(f"couldn't join {base} and {relative_path}")
        return joined.absolute()

    def join_repo_base(self, relative_path: str) -> str:
        return self._join_paths(
            base=self._env._repodir, relative_path=relative_path, enforce_existence=True
        )

    def join_output_base(self, relative_path: str) -> str:
        return self._join_paths(
            base=self._env._output_base,
            relative_path=relative_path,
            enforce_existence=True,
        )

    def hd_path(self, hd_name_or_path: str) -> str:
        if Instantiation.is_absolute_exists(hd_name_or_path):
            return hd_name_or_path
        path = self._join_paths(
            base=self._env._repodir,
            relative_path=f"/images/output-{hd_name_or_path}/{hd_name_or_path}",
            enforce_existence=True,
        )
        return path

    def cfgtar_path(self, sim: sim_base.Simulator) -> str:
        return f"{self._env._workdir}/cfg.{sim.name}.tar"

    def join_tmp_base(self, relative_path: str) -> str:
        return self._join_paths(
            base=self._env._tmp_simulation_files,
            relative_path=relative_path,
        )

    def dynamic_img_path(self, img: disk_images.DiskImage, format: str) -> str:
        filename = img._id + "." + format
        return self._join_paths(
            base=self._env._tmp_simulation_files,
            relative_path=filename,
        )

    def hdcopy_path(self, img: disk_images.DiskImage, format: str) -> str:
        filename = img._id + "_hdcopy" "." + format
        return self._join_paths(
            base=self._env._tmp_simulation_files,
            relative_path=filename,
        )

    def cpdir_subdir(self, sim: sim_base.Simulator) -> str:
        dir_path = f"/checkpoint.{sim.name}-{sim._id}"
        return self._join_paths(
            base=self.cpdir(), relative_path=dir_path, enforce_existence=False
        )

    def get_simulation_output_path(self, run_number: int) -> str:
        return self._join_paths(
            base=self._env._output_base,
            relative_path=f"out-{run_number}.json",
        )

    def find_sim_by_spec(self, spec: sys_host.FullSystemHost) -> sim_base.Simulator:
        return self._simulation.find_sim(spec)
