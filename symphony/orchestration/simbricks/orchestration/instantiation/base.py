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

from simbricks.orchestration.helpers import exceptions
from simbricks.orchestration.instantiation import dependency_graph as inst_dep_graph
from simbricks.orchestration.instantiation import fragment as inst_fragment
from simbricks.orchestration.instantiation import proxy as inst_proxy
from simbricks.orchestration.instantiation import socket as inst_socket
from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import eth as sys_eth
from simbricks.orchestration.system import mem as sys_mem
from simbricks.orchestration.system import pcie as sys_pcie
from simbricks.orchestration.system.host import disk_images
from simbricks.utils import base as utils_base
from simbricks.utils import file as utils_file

if typing.TYPE_CHECKING:
    from simbricks.orchestration.simulation import base as sim_base
    from simbricks.runtime import command_executor as cmd_exec


class InstantiationEnvironment(utils_base.IdObj):

    def __init__(
        self,
        workdir: pathlib.Path,
        simbricksdir: pathlib.Path,
    ):
        super().__init__()
        self._simbricks_dir: str = simbricksdir.resolve()
        self._work_dir: str = workdir.resolve()
        self._output_base: str = pathlib.Path(f"{self._work_dir}/output").resolve()
        self._tmp_dir: str = pathlib.Path(f"{self._work_dir}/tmp").resolve()
        self._img_dir: str = pathlib.Path(f"{self._tmp_dir}/imgs").resolve()
        self._cp_dir: str = pathlib.Path(f"{self._tmp_dir}/checkpoints").resolve()
        self._shm_base: str = pathlib.Path(f"{self._tmp_dir}/shm").resolve()
        self._proxy_dir = pathlib.Path(f"{self._tmp_dir}/proxies").resolve()

    # --------------------------------------------------
    # Read-only accessor functions for path properties -
    # --------------------------------------------------

    def repo_base(self, relative_path: str | None = None, must_exist: bool = True) -> str:
        if relative_path is None:
            return self._simbricks_dir
        return utils_file.join_paths(
            base=self._simbricks_dir, relative_path=relative_path, must_exist=must_exist
        )

    def work_dir(self, relative_path: str | None = None, must_exist: bool = False) -> str:
        if relative_path is None:
            return self._work_dir
        return utils_file.join_paths(
            base=self._work_dir, relative_path=relative_path, must_exist=must_exist
        )

    def output_base(self, relative_path: str | None = None, must_exist: bool = False) -> str:
        if relative_path is None:
            return self._output_base
        return utils_file.join_paths(
            base=self._output_base, relative_path=relative_path, must_exist=must_exist
        )

    def tmp_simulation_files(
        self, relative_path: str | None = None, must_exist: bool = False
    ) -> str:
        if relative_path is None:
            return self._tmp_dir
        return utils_file.join_paths(
            base=self._tmp_dir, relative_path=relative_path, must_exist=must_exist
        )

    def img_dir(self, relative_path: str | None = None, must_exist: bool = False) -> str:
        if relative_path is None:
            return self._img_dir
        return utils_file.join_paths(
            base=self._img_dir, relative_path=relative_path, must_exist=must_exist
        )

    def cp_dir(self, relative_path: str | None = None, must_exist: bool = False) -> str:
        if relative_path is None:
            return self._cp_dir
        return utils_file.join_paths(
            base=self._cp_dir, relative_path=relative_path, must_exist=must_exist
        )

    def shm_base(self, relative_path: str | None = None, must_exist: bool = False) -> str:
        if relative_path is None:
            return self._shm_base
        return utils_file.join_paths(
            base=self._shm_base, relative_path=relative_path, must_exist=must_exist
        )

    def proxy_dir(self, relative_path: str | None = None, must_exist: bool = False) -> str:
        if relative_path is None:
            return self._proxy_dir
        return utils_file.join_paths(
            base=self._proxy_dir, relative_path=relative_path, must_exist=must_exist
        )

    # ----------------------------------------
    # Other functions on instantiation paths -
    # ----------------------------------------

    def cfgtar_path(self, sim: sim_base.Simulator) -> str:
        return self.work_dir(f"cfg.{sim.name}.tar")

    def dynamic_img_path(self, img: disk_images.DiskImage, format: str) -> str:
        return self.img_dir(f"{img._id}.{format}")

    def hd_path(self, hd_name_or_path: str) -> str:
        if utils_file.is_absolute_exists(hd_name_or_path):
            return hd_name_or_path
        return self.repo_base(f"images/output-{hd_name_or_path}/{hd_name_or_path}", must_exist=True)

    def hdcopy_path(self, img: disk_images.DiskImage, format: str) -> str:
        return self.img_dir(f"{img._id}_hdcopy.{format}")

    def cpdir_sim(self, sim: sim_base.Simulator) -> str:
        return self.cp_dir(f"checkpoint.{sim.full_name()}-{sim._id}")

    def get_simulator_output_dir(self, sim: sim_base.Simulator) -> str:
        return self.output_base(f"output.{sim.full_name()}-{sim._id}")

    def get_simulator_shm_pool_path(self, sim: sim_base.Simulator) -> str:
        return self.shm_base(f"{sim.full_name()}-shm-pool-{sim._id}")

    def get_simulation_output_path(self) -> str:
        return self.output_base("out.json")


class Instantiation(utils_base.IdObj):

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
        self._proxy_pairs: list[inst_proxy.ProxyPair] = []
        self._inf_socktype_assignment: dict[sys_base.Interface, inst_socket.SockType] = {}

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
            return [fragment]
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

    def get_fragment(self, id: int) -> inst_fragment.Fragment:
        # TODO: add dict for fragments or change _fragments to dict so that we don't have to iterate here
        for fragment in self._fragments:
            if fragment.id() == id:
                return fragment
        # TODO: use more specific exception
        raise RuntimeError(f"could not find fragment with id {id}")

    def toJSON(self) -> dict:
        json_obj = super().toJSON()

        json_obj["simulation"] = self.simulation.id()

        fragments_json = []
        for fragment in self.fragments:
            utils_base.has_attribute(fragment, "toJSON")
            fragments_json.append(fragment.toJSON())
        json_obj["simulation_fragments"] = fragments_json

        json_obj["artifact_name"] = self.artifact_name
        json_obj["artifact_paths"] = self.artifact_paths

        json_obj["create_checkpoint"] = self._create_checkpoint
        json_obj["restore_checkpoint"] = self._restore_checkpoint
        json_obj["preserve_checkpoints"] = self._preserve_checkpoints
        json_obj["preserve_tmp_folder"] = self.preserve_tmp_folder

        inf_socktype_assignment = {}
        for inf, socktype in self._inf_socktype_assignment.items():
            inf_socktype_assignment[inf.id()] = socktype.value
        json_obj["inf_socktype_assignment"] = inf_socktype_assignment

        # TODO: serialize other fields etc. of interest
        return json_obj

    @classmethod
    def fromJSON(cls, sim: sim_base.Simulation, json_obj: dict) -> Instantiation:
        instance = super().fromJSON(json_obj)

        simulation_id = int(utils_base.get_json_attr_top(json_obj, "simulation"))
        assert simulation_id == sim.id()
        instance.simulation = sim

        instance.fragments = set()
        fragments_json = utils_base.get_json_attr_top(json_obj, "simulation_fragments")
        for frag_json in fragments_json:
            frag_class = utils_base.get_cls_by_json(frag_json)
            utils_base.has_attribute(frag_class, "fromJSON")
            frag = frag_class.fromJSON(frag_json, sim)
            instance.fragments.add(frag)

        instance.artifact_name = utils_base.get_json_attr_top(json_obj, "artifact_name")
        instance.artifact_paths = utils_base.get_json_attr_top(json_obj, "artifact_paths")

        instance._create_checkpoint = bool(
            utils_base.get_json_attr_top(json_obj, "create_checkpoint")
        )
        instance._restore_checkpoint = bool(
            utils_base.get_json_attr_top(json_obj, "restore_checkpoint")
        )
        instance._preserve_checkpoints = bool(
            utils_base.get_json_attr_top(json_obj, "preserve_checkpoints")
        )
        instance.preserve_tmp_folder = bool(
            utils_base.get_json_attr_top(json_obj, "preserve_tmp_folder")
        )

        inf_id_socktype_assignment: dict[int, str] = utils_base.get_json_attr_top(
            json_obj, "inf_socktype_assignment"
        )
        instance._inf_socktype_assignment = {}
        for inf_id, socktype_str in inf_id_socktype_assignment.items():
            inf = sim.system.get_inf(inf_id)
            socktype = inst_socket.SockType(socktype_str)
            instance._inf_socktype_assignment[inf] = socktype

        # TODO: deserialize other fields etc. of interest
        return instance

    def _opposing_interface_within_same_sim(self, interface: sys_base.Interface) -> bool:
        opposing_interface = interface.get_opposing_interface()
        component = interface.component
        opposing_component = opposing_interface.component
        assert interface is not opposing_interface
        return self.find_sim_by_spec(spec=component) == self.find_sim_by_spec(
            spec=opposing_component
        )

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
        return self.env.shm_base(f"{queue_type}-{queue_ident}")

    def get_socket(self, interface: sys_base.Interface) -> inst_socket.Socket:
        if self._opposing_interface_within_same_sim(interface=interface):
            raise exceptions.InstantiationExecutionError(
                "we do not create a socket for channels where both interfaces belong to the same simulator"
            )

        if interface in self._socket_per_interface:
            return self._socket_per_interface[interface]

        # create socket
        sock_path = self._interface_to_sock_path(interface=interface)
        new_socket = inst_socket.Socket(path=sock_path, ty=self.get_interface_socktype(interface))
        self._socket_per_interface[interface] = new_socket
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
        if self._assigned_fragment is None:
            # TODO: use more specific exception
            raise RuntimeError("Tried to access assigned fragment but there is no fragment "
                               "assigned yet")
        return self._assigned_fragment

    @assigned_fragment.setter
    def assigned_fragment(self, fragment: inst_fragment.Fragment) -> None:
        # TODO: check whether _assigned_fragment is already set?
        self._assigned_fragment = fragment

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
        cop._inf_socktype_assignment = self._inf_socktype_assignment
        return cop

    async def prepare(self) -> None:
        to_prepare = [self.env.shm_base, self.env.imgdir]
        if not self.create_checkpoint and not self.restore_checkpoint:
            to_prepare.append(self.env.cpdir)
        for tp in to_prepare:
            utils_file.rmtree(tp)
            utils_file.mkdir(tp)

        await self.simulation.prepare(inst=self)

    async def cleanup(self) -> None:
        if self.preserve_tmp_folder:
            return
        to_delete = [self.env.shm_base, self.env.imgdir]
        if not self._preserve_checkpoints:
            to_delete.append(self.env.cpdir)
        for td in to_delete:
            utils_file.rmtree(td)

    def find_sim_by_interface(self, interface: sys_base.Interface) -> sim_base.Simulator:
        return self.find_sim_by_spec(spec=interface.component)

    def find_sim_by_spec(self, spec: sys_base.Component) -> sim_base.Simulator:
        utils_base.has_expected_type(spec, sys_base.Component)
        return self.simulation.find_sim(spec)

    def create_proxy_pair(
        self,
        ProxyImplementation: type[inst_proxy.Proxy],
        fragment_a: inst_fragment.Fragment,
        fragment_b: inst_fragment.Fragment,
    ) -> inst_proxy.ProxyPair:
        """Create a pair of proxies for connecting two fragments. Can be invoked multiple times with
        the same two fragments to create multiple proxy connections between them."""
        proxy_a = ProxyImplementation()
        fragment_a.add_proxies(proxy_a)
        proxy_b = ProxyImplementation()
        fragment_b.add_proxies(proxy_b)
        pair = inst_proxy.ProxyPair(self, fragment_a, fragment_b, proxy_a, proxy_b)
        self._proxy_pairs.append(pair)
        return pair

    def get_proxy_pair(self, proxy: inst_proxy.Proxy) -> inst_proxy.ProxyPair:
        """Use given proxy to find previously created proxy pair."""
        for pair in self._proxy_pairs:
            if pair.proxy_a is proxy or pair.proxy_b is proxy:
                return pair
        raise exceptions.InstantiationConfigurationError("Cannot find previously added proxy pair.")

    def _find_opposing_proxy(self, proxy: inst_proxy.Proxy) -> inst_proxy.Proxy:
        pair = self.get_proxy_pair(proxy)
        return pair.proxy_a if pair.proxy_b is proxy else pair.proxy_b

    def _assign_interface_socktype(self) -> None:
        """For SimBricks sockets, assigns which interfaces listen and which connect."""
        for sim_a in self.simulation.all_simulators():
            for comp_a in sim_a.components():
                for inf_a in comp_a.interfaces():
                    # already assigned interface
                    if inf_a in self._inf_socktype_assignment:
                        continue

                    # both interfaces of channel are located in the same simulator
                    # => do not need to assign anything
                    if self._opposing_interface_within_same_sim(interface=inf_a):
                        continue

                    # get info on other side of channel
                    inf_b = inf_a.get_opposing_interface()
                    sim_b = self.find_sim_by_interface(inf_b)

                    # the actual assignment
                    # figure out supported socket types for both sides
                    supported_a = sim_a.supported_socket_types(inf_a)
                    supported_b = sim_b.supported_socket_types(inf_b)

                    # assign sockets as listening or connecting and add dependencies accordingly
                    if (
                        inst_socket.SockType.CONNECT in supported_a
                        and inst_socket.SockType.LISTEN in supported_b
                    ):
                        self._inf_socktype_assignment[inf_a] = inst_socket.SockType.CONNECT
                        self._inf_socktype_assignment[inf_b] = inst_socket.SockType.LISTEN
                    elif (
                        inst_socket.SockType.LISTEN in supported_a
                        and inst_socket.SockType.CONNECT in supported_b
                    ):
                        self._inf_socktype_assignment[inf_a] = inst_socket.SockType.LISTEN
                        self._inf_socktype_assignment[inf_b] = inst_socket.SockType.CONNECT
                    else:
                        raise exceptions.SimulationConfigurationError(
                            f"Cannot connect simulators {sim_a} and {sim_b} with supported proxy types {supported_a} and {supported_b}, respectively."
                        )

    def get_interface_socktype(self, inf: sys_base.Interface) -> inst_socket.SockType:
        if inf not in self._inf_socktype_assignment:
            raise exceptions.InstantiationConfigurationError(
                f"Interface {inf} does not have an assigned socket type."
            )
        return self._inf_socktype_assignment[inf]

    def finalize_validate(self) -> None:
        """This function can be invoked manually in the experiment script to validate system
        configuration, simulation configration, and instantiation early. Regardless, it is also
        always invoked before running an instantiation to do some final processing steps. To allow
        this, we guarantee idempotence, i.e. calling this function one or multiple times has the
        same effect."""
        self._assign_interface_socktype()
