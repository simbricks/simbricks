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


class Socket(util_base.IdObj):

    def __init__(self, path: str = "", ty: SockType = SockType.LISTEN):
        super().__init__()
        self._path = path
        self._type = ty


class InstantiationEnvironment(util_base.IdObj):

    def __init__(
        self,
        repo_path: str = pathlib.Path(__file__).parents[3].resolve(),
        workdir: str | None = None,
        output_base: str | None = None,
        cpdir: str | None = None,
        create_cp: bool = False,
        restore_cp: bool = False,
        shm_base: str | None = None,
        tmp_simulation_files: str | None = None,
        qemu_img_path: str | None = None,
        qemu_path: str | None = None,
    ):
        super().__init__()
        self._repodir: str = pathlib.Path(repo_path).resolve()
        self._workdir: str = (
            workdir if workdir else pathlib.Path(f"{self._repodir}/wrkdir").resolve()
        )
        self._output_base: str = (
            output_base
            if output_base
            else pathlib.Path(f"{self._workdir}/output").resolve()
        )
        self._cpdir: str = (
            cpdir
            if cpdir
            else pathlib.Path(f"{self._output_base}/checkpoints").resolve()
        )
        self._shm_base: str = (
            shm_base if shm_base else pathlib.Path(f"{self._workdir}/shm").resolve()
        )
        self._tmp_simulation_files: str = (
            tmp_simulation_files
            if tmp_simulation_files
            else (pathlib.Path(f"{self._workdir}/tmp").resolve())
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
        self._simulation_topo: (
            dict[sys_base.Interface, set[sys_base.Interface]] | None
        ) = None
        self._sim_dependency: (
            dict[sim_base.Simulator, set[sim_base.Simulator]] | None
        ) = None

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

    def qemu_img_path(self) -> str:
        return self._env._qemu_img_path

    def qemu_path(self) -> str:
        return self._env._qemu_path

    def _get_opposing_interface(
        self, interface: sys_base.Interface
    ) -> sys_base.Interface:
        opposing_inf = interface.get_opposing_interface()
        return opposing_inf

    def _opposing_interface_within_same_sim(
        self, interface: sys_base.Interface
    ) -> bool:
        opposing_interface = self._get_opposing_interface(interface=interface)
        component = interface.component
        opposing_component = opposing_interface.component
        assert interface is not opposing_interface
        return self.find_sim_by_spec(spec=component) == self.find_sim_by_spec(
            spec=opposing_component
        )

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
        channel = interface.get_chan_raise()
        queue_ident = f"{channel.a._id}.{channel._id}.{channel.b._id}"

        queue_type = None
        match interface:
            case sys_pcie.PCIeHostInterface() | sys_pcie.PCIeDeviceInterface():
                queue_type = "pci"
            case sys_mem.MemDeviceInterface() | sys_mem.MemHostInterface():
                queue_type = "mem"
            case sys_eth.EthInterface():
                queue_type = "eth"
            case _:
                raise Exception("cannot create socket path for given interface type")

        assert queue_type is not None
        print(f"_interface_to_sock_path: self._env._shm_base={self.shm_base_dir()}")
        return self._join_paths(
            base=self.shm_base_dir(),
            relative_path=f"{queue_type}-{queue_ident}",
            enforce_existence=False,
        )

    def _create_opposing_socket(self, socket: Socket, socket_type: SockType) -> Socket:
        new_ty = (
            SockType.LISTEN if socket._type == SockType.CONNECT else SockType.CONNECT
        )
        if new_ty != socket_type:
            raise Exception(
                f"cannot create opposing socket, as required type is not supported: required={new_ty.name}, supported={socket_type.name}"
            )
        new_path = socket._path
        new_socket = Socket(path=new_path, ty=new_ty)
        return new_socket

    def get_socket(self, interface: sys_base.Interface) -> Socket | None:
        socket = self._get_socket_by_interface(interface=interface)
        if socket:
            return socket
        return None

    def _get_socket(
        self, interface: sys_base.Interface, socket_type: SockType
    ) -> Socket:

        if self._opposing_interface_within_same_sim(interface=interface):
            raise Exception(
                "we do not create a socket for interfacces taht both beloing to the same simulator"
            )

        # check if already a socket is associated with this interface
        socket = self._get_socket_by_interface(interface=interface)
        if socket is not None:
            return socket

        # Check if other side already created a socket, and create an opposing one
        socket = self._get_opposing_socket_by_interface(interface=interface)
        if socket is not None:
            new_socket = self._create_opposing_socket(
                socket=socket, socket_type=socket_type
            )
            self._updated_tracker_mapping(interface=interface, socket=new_socket)
            print(f"created socket: {new_socket._path}")
            return new_socket

        # create socket if opposing socket was not created yet
        sock_path = self._interface_to_sock_path(interface=interface)
        new_socket = Socket(path=sock_path, ty=socket_type)
        self._updated_tracker_mapping(interface=interface, socket=new_socket)
        print(f"created socket: {new_socket._path}")
        return new_socket

    def _build_simulation_topology(self) -> None:

        sim_dependency: dict[sim_base.Simulator, set[sim_base.Simulator]] = {}

        def insert_dependency(
            sim_a: sim_base.Simulator, depends_on: sim_base.Simulator
        ):
            if depends_on in sim_dependency:
                if sim_a in sim_dependency[depends_on]:
                    # TODO: FIXME
                    raise Exception(
                        "detected cylic dependency, this is currently not supported"
                    )

            a_dependencies = set()
            if sim_a in sim_dependency:
                a_dependencies = sim_dependency[sim_a]

            a_dependencies.add(depends_on)
            sim_dependency[sim_a] = a_dependencies

        def update_a_depends_on_b(inf_a: sys_base.Interface, inf_b: sys_base.Interface):
            sim_a = self.find_sim_by_interface(interface=inf_a)
            sim_b = self.find_sim_by_interface(interface=inf_b)
            a_sock: set[SockType] = sim_a.supported_socket_types(interface=inf_a)
            b_sock: set[SockType] = sim_b.supported_socket_types(interface=inf_b)

            if a_sock != b_sock:
                if len(a_sock) == 0 or len(b_sock) == 0:
                    raise Exception(
                        "cannot create socket and resolve dependency if no socket type is supported for an interface"
                    )
                if SockType.CONNECT in a_sock:
                    assert SockType.LISTEN in b_sock
                    insert_dependency(sim_a, depends_on=sim_b)
                    self._get_socket(interface=inf_a, socket_type=SockType.CONNECT)
                    self._get_socket(interface=inf_b, socket_type=SockType.LISTEN)
                else:
                    assert SockType.CONNECT in b_sock
                    insert_dependency(sim_b, depends_on=sim_a)
                    self._get_socket(interface=inf_b, socket_type=SockType.CONNECT)
                    self._get_socket(interface=inf_a, socket_type=SockType.LISTEN)
            else:
                # deadlock?
                if len(a_sock) != 2 or len(b_sock) != 2:
                    raise Exception("cannot solve deadlock")
                # both support both we just pick an order
                insert_dependency(sim_a, depends_on=sim_b)
                self._get_socket(interface=sim_a, socket_type=SockType.CONNECT)
                self._get_socket(interface=sim_b, socket_type=SockType.LISTEN)

        # build dependency graph
        for sim in self._simulation.all_simulators():
            for comp in sim._components:
                for sim_inf in comp.interfaces():
                    if self._opposing_interface_within_same_sim(interface=sim_inf):
                        continue
                    opposing_inf = self._get_opposing_interface(interface=sim_inf)
                    update_a_depends_on_b(inf_a=sim_inf, inf_b=opposing_inf)

        self._sim_dependency = sim_dependency

    def sim_dependencies(self) -> dict[sim_base.Simulator, set[sim_base.Simulator]]:
        if self._sim_dependency is not None:
            return self._sim_dependency

        self._build_simulation_topology()
        assert self._sim_dependency is not None
        return self._sim_dependency

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

    # TODO: fix paths to support mutliple exeriment runs etc.
    def wrkdir(self) -> str:
        return pathlib.Path(self._env._workdir).resolve()

    def shm_base_dir(self) -> str:
        return pathlib.Path(self._env._shm_base).resolve()

    def create_cp(self) -> bool:
        return self._env._create_cp

    def restore_cp(self) -> bool:
        return self._env._restore_cp

    def cpdir(self) -> str:
        return pathlib.Path(self._env._cpdir).resolve()

    def wrkdir(self) -> str:
        return pathlib.Path(self._env._workdir).resolve()

    def tmp_dir(self) -> str:
        return pathlib.Path(self._env._tmp_simulation_files).resolve()

    async def prepare(self) -> None:
        wrkdir = self.wrkdir()
        print(f"wrkdir={wrkdir}")
        shutil.rmtree(wrkdir, ignore_errors=True)
        await self.executor.rmtree(wrkdir)

        shm_base = self.shm_base_dir()
        print(f"shm_base={shm_base}")
        shutil.rmtree(shm_base, ignore_errors=True)
        await self.executor.rmtree(shm_base)

        cpdir = self.cpdir()
        print(f"cpdir={cpdir}")
        if self.create_cp():
            shutil.rmtree(cpdir, ignore_errors=True)
            await self.executor.rmtree(cpdir)

        tmpdir = self.tmp_dir()
        print(f"tmpdir={tmpdir}")
        shutil.rmtree(tmpdir, ignore_errors=True)
        await self.executor.rmtree(tmpdir)

        pathlib.Path(wrkdir).mkdir(parents=True, exist_ok=True)
        await self.executor.mkdir(wrkdir)

        pathlib.Path(cpdir).mkdir(parents=True, exist_ok=True)
        await self.executor.mkdir(cpdir)

        pathlib.Path(shm_base).mkdir(parents=True, exist_ok=True)
        await self.executor.mkdir(shm_base)

        pathlib.Path(tmpdir).mkdir(parents=True, exist_ok=True)
        await self.executor.mkdir(tmpdir)

        await self._simulation.prepare(inst=self)

    async def cleanup(self) -> None:
        pass  # TODO: implement cleanup functionality (e.g. delete )

    def _join_paths(
        self, base: str = "", relative_path: str = "", enforce_existence=False
    ) -> str:
        if relative_path.startswith("/"):
            raise Exception(
                f"cannot join with base={base} because relative_path={relative_path} starts with '/'"
            )

        joined = pathlib.Path(base).joinpath(relative_path).resolve()
        if enforce_existence and not joined.exists():
            raise Exception(f"couldn't join {base} and {relative_path}")
        return joined.as_posix()

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
            relative_path=f"images/output-{hd_name_or_path}/{hd_name_or_path}",
            enforce_existence=True,
        )
        return path

    def cfgtar_path(self, sim: sim_base.Simulator) -> str:
        return f"{self.wrkdir()}/cfg.{sim.name}.tar"

    def join_tmp_base(self, relative_path: str) -> str:
        return self._join_paths(
            base=self.tmp_dir(),
            relative_path=relative_path,
        )

    def dynamic_img_path(self, img: disk_images.DiskImage, format: str) -> str:
        filename = f"{img._id}.{format}"
        return self._join_paths(
            base=self.tmp_dir(),
            relative_path=filename,
        )

    def hdcopy_path(self, img: disk_images.DiskImage, format: str) -> str:
        filename = f"{img._id}_hdcopy.{format}"
        return self._join_paths(
            base=self.tmp_dir(),
            relative_path=filename,
        )

    def cpdir_subdir(self, sim: sim_base.Simulator) -> str:
        dir_path = f"checkpoint.{sim.full_name()}-{sim._id}"
        return self._join_paths(
            base=self.cpdir(), relative_path=dir_path, enforce_existence=False
        )

    def get_simmulator_output_dir(self, sim: sim_base.Simulator) -> str:
        dir_path = f"output.{sim.full_name()}-{sim._id}"
        return self._join_paths(base=self._env._output_base, relative_path=dir_path)

    def get_simulator_shm_pool_path(self, sim: sim_base.Simulator) -> str:
        return self._join_paths(
            base=self.shm_base_dir(),
            relative_path=f"{sim.full_name()}-shm-pool-{sim._id}",
        )

    def get_simulation_output_path(self, run_number: int) -> str:
        return self._join_paths(
            base=self._env._output_base,
            relative_path=f"out-{run_number}.json",
        )

    def find_sim_by_interface(
        self, interface: sys_base.Interface
    ) -> sim_base.Simulator:
        return self.find_sim_by_spec(spec=interface.component)

    def find_sim_by_spec(self, spec: sys_base.Component) -> sim_base.Simulator:
        util_base.has_expected_type(spec, sys_base.Component)
        return self._simulation.find_sim(spec)
