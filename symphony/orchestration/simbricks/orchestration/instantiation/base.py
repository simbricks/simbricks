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

import copy
import pathlib
import typing
import uuid

from simbricks.orchestration.instantiation import dependency_graph as inst_dep_graph
from simbricks.orchestration.instantiation import fragment as inst_fragment
from simbricks.orchestration.instantiation import proxy as inst_proxy
from simbricks.orchestration.instantiation import socket as inst_socket
from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import eth as sys_eth
from simbricks.orchestration.system import mem as sys_mem
from simbricks.orchestration.system import pcie as sys_pcie
from simbricks.orchestration.system.host import disk_images
from simbricks.utils import base as util_base
from simbricks.utils import file as util_file

if typing.TYPE_CHECKING:
    from simbricks.orchestration.simulation import base as sim_base
    from simbricks.runtime import command_executor as cmd_exec


class InstantiationEnvironment(util_base.IdObj):

    def __init__(
        self,
        workdir: pathlib.Path = pathlib.Path.cwd() / pathlib.Path("simbricks-workdir"),
        simbricksdir: pathlib.Path = pathlib.Path("/simbricks"),
    ):
        super().__init__()
        self._simbricksdir: str = simbricksdir.resolve()
        self._workdir: str = workdir.resolve()
        self._output_base: str = pathlib.Path(f"{self._workdir}/output").resolve()
        self._tmp_simulation_files: str = pathlib.Path(f"{self._workdir}/tmp").resolve()
        self._imgdir: str = pathlib.Path(f"{self._tmp_simulation_files}/imgs").resolve()
        self._cpdir: str = pathlib.Path(f"{self._tmp_simulation_files}/checkpoints").resolve()
        self._shm_base: str = pathlib.Path(f"{self._tmp_simulation_files}/shm").resolve()


class Instantiation(util_base.IdObj):

    def __init__(
        self,
        sim: sim_base.Simulation,
    ):
        super().__init__()
        self.simulation: sim_base.Simulation = sim
        self._fragments: list[inst_fragment.Fragment] | None = None
        self._assigned_fragment: inst_fragment.Fragment | None = None
        """The fragment that is actually executed. This is set by the runner and can also be a
        merged fragment."""
        self.env: InstantiationEnvironment | None = None
        self.artifact_name: str = f"simbricks-artifact-{str(uuid.uuid4())}.zip"
        self.artifact_paths: list[str] = []
        self._create_checkpoint: bool = False
        self._restore_checkpoint: bool = False
        self._preserve_checkpoints: bool = True
        self.preserve_tmp_folder: bool = False
        # NOTE: temporary data structure
        self._socket_per_interface: dict[sys_base.Interface, inst_socket.Socket] = {}
        # NOTE: temporary data structure
        self._sim_dependency: inst_dep_graph.SimulationDependencyGraph | None = None
        self._cmd_executor: cmd_exec.CommandExecutorFactory | None = None

    @property
    def create_artifact(self) -> bool:
        return len(self.artifact_paths) > 0

    @property
    def command_executor(self) -> cmd_exec.CommandExecutorFactory:
        if self._cmd_executor is None:
            raise RuntimeError(f"{type(self).__name__}._cmd_executor should be set")
        return self._cmd_executor

    @property
    def fragments(self) -> list[inst_fragment.Fragment]:
        if self._fragments is None:
            # Default fragment contains all simulators
            fragment = inst_fragment.Fragment()
            fragment.add_simulators(*self.simulation.all_simulators())
            return fragment
        return self._fragments

    @fragments.setter
    def fragments(self, new_val: list[inst_fragment.Fragment]) -> None:
        if not new_val:
            raise RuntimeError("List of fragments cannot be empty")

        # Check that fragments do not overlap
        sims_seen = set()
        sims_ambiguous = set()
        for fragment in new_val:
            sims_ambiguous.update(sims_seen.intersection(fragment.all_simulators()))
            sims_seen.update(fragment.all_simulators())
        if sims_ambiguous:
            raise RuntimeError(
                f"Fragments must not overlap. The following simulators appear in multiple fragments: {sims_ambiguous}"
            )

        # Check that all simulators occur in some fragment
        sims_missing = set(self.simulation.all_simulators()).difference(sims_seen)
        if sims_missing:
            raise RuntimeError(
                f"Fragments must be complete. The following simulators do not appear in any fragment: {sims_missing}"
            )

        self._fragments = new_val

    def toJSON(self) -> dict:
        json_obj = super().toJSON()

        json_obj["simulation"] = self.simulation.id()

        fragments_json = []
        if len(self.fragments) < 1:
            fragment = self.assigned_fragment
            util_base.has_attribute(fragment, "toJSON")
            fragments_json.append(fragment.toJSON())
        else:
            for fragment in self.fragments:
                util_base.has_attribute(fragment, "toJSON")
                fragments_json.append(fragment.toJSON())
        json_obj["simulation_fragments"] = fragments_json

        json_obj["artifact_name"] = self.artifact_name
        json_obj["artifact_paths"] = self.artifact_paths

        json_obj["create_checkpoint"] = self._create_checkpoint
        json_obj["restore_checkpoint"] = self._restore_checkpoint
        json_obj["preserve_checkpoints"] = self._preserve_checkpoints
        json_obj["preserve_tmp_folder"] = self.preserve_tmp_folder

        # TODO: serialize other fields etc. of interest
        return json_obj

    @classmethod
    def fromJSON(cls, sim: sim_base.Simulation, json_obj: dict) -> Instantiation:
        instance = super().fromJSON(json_obj)

        simulation_id = int(util_base.get_json_attr_top(json_obj, "simulation"))
        assert simulation_id == sim.id()
        instance.simulation = sim

        instance.fragments = set()
        fragments_json = util_base.get_json_attr_top(json_obj, "simulation_fragments")
        for frag_json in fragments_json:
            frag_class = util_base.get_cls_by_json(frag_json)
            util_base.has_attribute(frag_class, "fromJSON")
            frag = frag_class.fromJSON(frag_json)
            instance.fragments.add(frag)

        instance.artifact_name = util_base.get_json_attr_top(json_obj, "artifact_name")
        instance.artifact_paths = util_base.get_json_attr_top(json_obj, "artifact_paths")

        instance._create_checkpoint = bool(
            util_base.get_json_attr_top(json_obj, "create_checkpoint")
        )
        instance._restore_checkpoint = bool(
            util_base.get_json_attr_top(json_obj, "restore_checkpoint")
        )
        instance._preserve_checkpoints = bool(
            util_base.get_json_attr_top(json_obj, "preserve_checkpoints")
        )
        instance.preserve_tmp_folder = bool(
            util_base.get_json_attr_top(json_obj, "preserve_tmp_folder")
        )
        # TODO: deserialize other fields etc. of interest
        return instance

    def _get_opposing_interface(self, interface: sys_base.Interface) -> sys_base.Interface:
        opposing_inf = interface.get_opposing_interface()
        return opposing_inf

    def _opposing_interface_within_same_sim(self, interface: sys_base.Interface) -> bool:
        opposing_interface = self._get_opposing_interface(interface=interface)
        component = interface.component
        opposing_component = opposing_interface.component
        assert interface is not opposing_interface
        return self.find_sim_by_spec(spec=component) == self.find_sim_by_spec(
            spec=opposing_component
        )

    def _updated_tracker_mapping(
        self, interface: sys_base.Interface, socket: inst_socket.Socket
    ) -> None:
        # update interface mapping
        if interface in self._socket_per_interface:
            raise Exception("an interface cannot be associated with two sockets")
        self._socket_per_interface[interface] = socket

    def _get_socket_by_interface(self, interface: sys_base.Interface) -> inst_socket.Socket | None:
        if interface not in self._socket_per_interface:
            return None
        return self._socket_per_interface[interface]

    def _get_opposing_socket_by_interface(
        self, interface: sys_base.Interface
    ) -> inst_socket.Socket | None:
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
        return self._join_paths(
            base=self.shm_base_dir(),
            relative_path=f"{queue_type}-{queue_ident}",
            enforce_existence=False,
        )

    def _create_opposing_socket(
        self, socket: inst_socket.Socket, socket_type: inst_socket.SockType
    ) -> inst_socket.Socket:
        new_ty = (
            inst_socket.SockType.LISTEN
            if socket._type == inst_socket.SockType.CONNECT
            else inst_socket.SockType.CONNECT
        )
        if new_ty != socket_type:
            raise Exception(
                f"cannot create opposing socket, as required type is not supported: required={new_ty.name}, supported={socket_type.name}"
            )
        new_path = socket._path
        new_socket = inst_socket.Socket(path=new_path, ty=new_ty)
        return new_socket

    def update_get_socket(self, interface: sys_base.Interface) -> inst_socket.Socket | None:
        socket = self._get_socket_by_interface(interface=interface)
        if socket:
            return socket
        return None

    def _update_get_socket(
        self, interface: sys_base.Interface, socket_type: inst_socket.SockType
    ) -> inst_socket.Socket:

        if self._opposing_interface_within_same_sim(interface=interface):
            raise Exception(
                "we do not create a socket for channels where both interfaces belong to the same simulator"
            )

        # check if already a socket is associated with this interface
        socket = self._get_socket_by_interface(interface=interface)
        if socket is not None:
            return socket

        # Check if other side already created a socket, and create an opposing one
        socket = self._get_opposing_socket_by_interface(interface=interface)
        if socket is not None:
            new_socket = self._create_opposing_socket(socket=socket, socket_type=socket_type)
            self._updated_tracker_mapping(interface=interface, socket=new_socket)
            return new_socket

        # create socket if opposing socket was not created yet
        sock_path = self._interface_to_sock_path(interface=interface)
        new_socket = inst_socket.Socket(path=sock_path, ty=socket_type)
        self._updated_tracker_mapping(interface=interface, socket=new_socket)
        return new_socket

    def sim_dependencies(self) -> inst_dep_graph.SimulationDependencyGraph:
        if self._sim_dependency is not None:
            return self._sim_dependency
        self._sim_dependency = inst_dep_graph.build_simulation_dependency_graph(self)
        return self._sim_dependency

    @property
    def create_checkpoint(self) -> bool:
        """
        Whether to use checkpoint and restore for simulators.

        The most common use-case for this is accelerating host simulator startup
        by first running in a less accurate mode, then checkpointing the system
        state after boot and running simulations from there.
        """
        assert (self._create_checkpoint ^ self._restore_checkpoint) or (
            not self._create_checkpoint and not self._restore_checkpoint
        )
        return self._create_checkpoint

    @create_checkpoint.setter
    def create_checkpoint(self, create_checkpoint: bool) -> None:
        assert (self._create_checkpoint ^ self._restore_checkpoint) or (
            not self._create_checkpoint and not self._restore_checkpoint
        )
        self._create_checkpoint = create_checkpoint

    @property
    def restore_checkpoint(self) -> bool:
        assert (self._create_checkpoint ^ self._restore_checkpoint) or (
            not self._create_checkpoint and not self._restore_checkpoint
        )
        return self._restore_checkpoint

    @restore_checkpoint.setter
    def restore_checkpoint(self, restore_checkpoint: bool) -> None:
        assert (self._create_checkpoint ^ self._restore_checkpoint) or (
            not self._create_checkpoint and not self._restore_checkpoint
        )
        self._restore_checkpoint = restore_checkpoint

    @property
    def assigned_fragment(self) -> inst_fragment.Fragment:
        if self._assigned_fragment is not None:
            return self._assigned_fragment

        if not self.fragments:
            # Experiment does not define any simulation fragments, so
            # implicitly, we create one fragment that spans the whole simulation
            self._assigned_fragment = inst_fragment.Fragment()
            self._assigned_fragment.add_simulators(*self.simulation.all_simulators())
        else:
            assert self._assigned_fragment is not None, "Runner must set assigned fragment"
        return self._assigned_fragment

    # TODO: this needs fixing...
    def copy(self) -> Instantiation:
        cop = Instantiation(sim=self.simulation)
        cop.simulation = copy.deepcopy(
            self.simulation
        )  # maybe there is a smarter way of achieving this...
        cop.artifact_name = self.artifact_name
        cop.artifact_paths = self.artifact_paths
        cop._create_checkpoint = self._create_checkpoint
        cop._restore_checkpoint = self._restore_checkpoint
        cop._preserve_checkpoints = self._preserve_checkpoints
        cop.preserve_tmp_folder = self.preserve_tmp_folder
        cop._socket_per_interface = {}
        cop._sim_dependency = None
        return cop

    def out_base_dir(self) -> str:
        return pathlib.Path(f"{self.env._output_base}/{self.simulation.name}/{self._id}").resolve()

    def shm_base_dir(self) -> str:
        return pathlib.Path(f"{self.env._shm_base}/{self.simulation.name}/{self._id}").resolve()

    def imgs_dir(self) -> str:
        return pathlib.Path(f"{self.env._imgdir}/{self.simulation.name}/{self._id}").resolve()

    def cpdir(self) -> str:
        return pathlib.Path(f"{self.env._cpdir}/{self.simulation.name}").resolve()  # /{self._id}"

    def wrkdir(self) -> str:
        return pathlib.Path(f"{self.env._workdir}/{self.simulation.name}").resolve()  # /{self._id}"

    async def prepare(self) -> None:
        to_prepare = [self.shm_base_dir(), self.imgs_dir()]
        if not self.create_checkpoint and not self.restore_checkpoint:
            to_prepare.append(self.cpdir())
        for tp in to_prepare:
            util_file.rmtree(tp)
            util_file.mkdir(tp)

        await self.simulation.prepare(inst=self)

    async def cleanup(self) -> None:
        if self.preserve_tmp_folder:
            return
        to_delete = [self.shm_base_dir(), self.imgs_dir()]
        if not self._preserve_checkpoints:
            to_delete.append(self.cpdir())
        for td in to_delete:
            util_file.rmtree(td)

    def _join_paths(self, base: str = "", relative_path: str = "", enforce_existence=False) -> str:
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
            base=self.env._simbricksdir, relative_path=relative_path, enforce_existence=True
        )

    def join_output_base(self, relative_path: str) -> str:
        return self._join_paths(
            base=self.out_base_dir(),
            relative_path=relative_path,
            enforce_existence=True,
        )

    def hd_path(self, hd_name_or_path: str) -> str:
        if util_file.is_absolute_exists(hd_name_or_path):
            return hd_name_or_path
        path = self._join_paths(
            base=self.env._simbricksdir,
            relative_path=f"images/output-{hd_name_or_path}/{hd_name_or_path}",
            enforce_existence=True,
        )
        return path

    def cfgtar_path(self, sim: sim_base.Simulator) -> str:
        return f"{self.wrkdir()}/cfg.{sim.name}.tar"

    # def join_tmp_base(self, relative_path: str) -> str:
    #     return self._join_paths(
    #         base=self.tmp_dir(),
    #         relative_path=relative_path,
    #     )

    def join_imgs_path(self, relative_path: str) -> str:
        return self._join_paths(
            base=self.imgs_dir(),
            relative_path=relative_path,
        )

    def dynamic_img_path(self, img: disk_images.DiskImage, format: str) -> str:
        filename = f"{img._id}.{format}"
        return self._join_paths(
            base=self.imgs_dir(),
            relative_path=filename,
        )

    def hdcopy_path(self, img: disk_images.DiskImage, format: str) -> str:
        filename = f"{img._id}_hdcopy.{format}"
        return self._join_paths(
            base=self.imgs_dir(),
            relative_path=filename,
        )

    def cpdir_subdir(self, sim: sim_base.Simulator) -> str:
        dir_path = f"checkpoint.{sim.full_name()}-{sim._id}"
        return self._join_paths(base=self.cpdir(), relative_path=dir_path, enforce_existence=False)

    def get_simulator_output_dir(self, sim: sim_base.Simulator) -> str:
        dir_path = f"output.{sim.full_name()}-{sim._id}"
        return self._join_paths(base=self.out_base_dir(), relative_path=dir_path)

    def get_simulator_shm_pool_path(self, sim: sim_base.Simulator) -> str:
        return self._join_paths(
            base=self.shm_base_dir(),
            relative_path=f"{sim.full_name()}-shm-pool-{sim._id}",
        )

    def get_simulation_output_path(self) -> str:
        return self._join_paths(
            base=self.out_base_dir(),
            relative_path=f"out.json",
        )

    def find_sim_by_interface(self, interface: sys_base.Interface) -> sim_base.Simulator:
        return self.find_sim_by_spec(spec=interface.component)

    def find_sim_by_spec(self, spec: sys_base.Component) -> sim_base.Simulator:
        util_base.has_expected_type(spec, sys_base.Component)
        return self.simulation.find_sim(spec)

    def create_proxy_pair(
        self,
        ProxyClass: type[inst_proxy.Proxy],
        fragment_a: inst_fragment.Fragment,
        fragment_b: inst_fragment.Fragment,
    ) -> inst_proxy.ProxyPair:
        """Create a pair of proxies for connecting two fragments. Can be invoked multiple times with
        the same two fragments to create multiple proxy connections between them."""
        # TODO (Jonas) Implement this.
        pass
