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

from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import eth as sys_eth
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.utils import base as base_utils


class NetSim(sim_base.Simulator):
    """Base class for network simulators."""

    def __init__(
        self,
        simulation: sim_base.Simulation,
        executable: str,
        name: str = "",
    ) -> None:
        super().__init__(simulation=simulation, executable=executable, name=name)

    def full_name(self) -> str:
        return "net." + self.name

    def init_network(self) -> None:
        pass

    def supported_socket_types(
        self, interface: sys_base.Interface
    ) -> set[inst_base.SockType]:
        return [inst_base.SockType.CONNECT]

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> NetSim:
        return super().fromJSON(simulation, json_obj)


class WireNet(NetSim):

    def __init__(
        self, simulation: sim_base.Simulation, relative_pcap_filepath: str | None = None
    ) -> None:
        super().__init__(
            simulation=simulation,
            executable="sims/net/wire/net_wire",
        )
        self.name = f"WireNet-{self._id}"
        self._relative_pcap_file_path: str | None = relative_pcap_filepath

    def add(self, wire: sys_eth.EthWire):
        base_utils.has_expected_type(wire, sys_eth.EthWire)
        if len(self._components) > 1:
            raise Exception(
                "can only add a single wire component to the WireNet simulator"
            )
        super().add(wire)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["relative_pcap_file_path"] = self._relative_pcap_file_path
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> WireNet:
        instance = super().fromJSON(simulation, json_obj)
        # TODO: FIXME
        return instance

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        channels = self.get_channels()
        eth_latency, sync_period, run_sync = (
            sim_base.Simulator.get_unique_latency_period_sync(channels=channels)
        )

        sockets = self._get_socks_by_all_comp(inst=inst)
        assert len(sockets) == 2

        cmd = inst.join_repo_base(self._executable)
        cmd += f"{sockets[0]._path} {sockets[1]._path} {run_sync} {sync_period} {eth_latency}"

        if self._relative_pcap_file_path is not None:
            pcap_file = inst.join_output_base(
                relative_path=self._relative_pcap_file_path
            )
            cmd += " " + pcap_file
        return cmd


class SwitchNet(NetSim):

    def __init__(
        self,
        simulation: sim_base.Simulation,
        executable: str = "sims/net/switch/net_switch",
        relative_pcap_filepath: str | None = None,
    ) -> None:
        super().__init__(
            simulation=simulation,
            executable=executable,
        )
        self.name = f"SwitchNet-{self._id}"
        self._relative_pcap_file_path: str | None = relative_pcap_filepath

    def add(self, switch_spec: sys_eth.EthSwitch):
        base_utils.has_expected_type(switch_spec, sys_eth.EthSwitch)
        if len(self._components) > 1:
            raise Exception("can only add a single switch component to the SwitchNet")
        super().add(switch_spec)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["relative_pcap_file_path"] = self._relative_pcap_file_path
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> SwitchNet:
        instance = super().fromJSON(simulation, json_obj)
        # TODO: FIXME
        return instance

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        channels = self.get_channels()
        eth_latency, sync_period, run_sync = (
            sim_base.Simulator.get_unique_latency_period_sync(channels=channels)
        )

        cmd = inst.join_repo_base(self._executable)
        cmd += f" -S {sync_period} -E {eth_latency}"

        if not run_sync:
            cmd += " -u"

        if self._relative_pcap_file_path is not None:
            pcap_file = inst.join_output_base(
                relative_path=self._relative_pcap_file_path
            )
            cmd += " " + pcap_file

        sockets = self._get_socks_by_all_comp(inst=inst)
        listen, connect = sim_base.Simulator.split_sockets_by_type(sockets)

        for sock in connect:
            cmd += " -s " + sock._path

        for sock in listen:
            cmd += " -h " + sock._path

        return cmd


class MemSwitchNet(SwitchNet):

    def __init__(
        self, simulation: sim_base.Simulation, relative_pcap_file_path=None
    ) -> None:
        super().__init__(
            simulation=simulation,
            executable="sims/mem/memswitch/memswitch",
            relative_pcap_file_path=relative_pcap_file_path,
        )
        self.name = f"MemSwitchNet-{self._id}"
        """AS_ID,VADDR_START,VADDR_END,MEMNODE_MAC,PHYS_START."""
        self.mem_map = []

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> MemSwitchNet:
        instance = super().fromJSON(simulation, json_obj)
        # TODO: FIXME
        return instance

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst)

        for m in self.mem_map:
            cmd += " -m " + f" {m[0]},{m[1]},{m[2]},"
            cmd += "".join(reversed(m[3].split(":")))
            cmd += f",{m[4]}"

        return cmd


class SimpleNS3Sim(NetSim):

    def __init__(
        self,
        simulation: sim_base.Simulation,
        name: str = "SimpleNS3Sim",
        ns3_run_script: str = "",
    ) -> None:
        super().__init__(
            simulation=simulation,
            executable="sims/external/ns-3/simbricks-run.sh",
            name=name,
        )
        self._ns3_run_script: str = ns3_run_script
        self.opt: str | None = None

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["ns3_run_script"] = self._ns3_run_script
        json_obj["opt"] = self.opt
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> SimpleNS3Sim:
        instance = super().fromJSON(simulation, json_obj)
        instance._ns3_run_script = base_utils.get_json_attr_top(
            json_obj, "ns3_run_script"
        )
        instance.opt = base_utils.get_json_attr_top_or_none(json_obj, "opt")
        return instance

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        return f"{inst.join_repo_base(self._executable)} {self._ns3_run_script} "


class NS3DumbbellNet(SimpleNS3Sim):

    def __init__(self, simulation: sim_base.Simulation) -> None:
        super().__init__(
            simulation=simulation,
            ns3_run_script="simbricks-dumbbell-example",
        )
        self.name = f"NS3DumbbellNet-{self._id}"
        self._left: sys_eth.EthSwitch | None = None
        self._right: sys_eth.EthSwitch | None = None

    def add(self, left: sys_eth.EthSwitch, right: sys_eth.EthSwitch):
        base_utils.has_expected_type(left, sys_eth.EthSwitch)
        base_utils.has_expected_type(right, sys_eth.EthSwitch)

        if (
            len(self._components) > 2
            or self._left is not None
            or self._right is not None
        ):
            raise Exception("NS3DumbbellNet can only simulate two switches")

        super().add(comp=left)
        super().add(comp=right)
        self._left = left
        self._right = right

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["left"] = self._left.id()
        json_obj["right"] = self._right.id()
        return json_obj

    @classmethod
    def fromJSON(
        cls, simulation: sim_base.Simulation, json_obj: dict
    ) -> NS3DumbbellNet:
        instance = super().fromJSON(simulation, json_obj)
        left_id = int(base_utils.get_json_attr_top(json_obj, "left"))
        instance._left = json_obj["left"] = simulation.system.get_comp(left_id)
        right_id = int(base_utils.get_json_attr_top(json_obj, "right"))
        instance._right = json_obj["right"] = simulation.system.get_comp(right_id)
        return instance

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst=inst)

        left_socks = self._get_socks_by_comp(inst=inst, comp=self._left)
        for sock in left_socks:
            assert sock._type == inst_base.SockType.CONNECT
            cmd += f"--SimbricksPortLeft={sock._path} "

        right_sockets = self._get_socks_by_comp(inst=inst, comp=self._right)
        for sock in right_sockets:
            assert sock._type == inst_base.SockType.CONNECT
            cmd += f"--SimbricksPortRight={sock._path} "

        if self.opt is not None:
            cmd += f"{self.opt}"

        print(cmd)
        return cmd


class NS3BridgeNet(SimpleNS3Sim):

    def __init__(self, simulation: sim_base.Simulation) -> None:
        super().__init__(
            simulation=simulation,
            ns3_run_script="simbricks-bridge-example",
        )
        self.name = f"NS3BridgeNet-{self._id}"

    def add(self, switch_comp: sys_eth.EthSwitch):
        base_utils.has_expected_type(switch_comp, sys_eth.EthSwitch)
        if len(self._components) > 1:
            raise Exception("NS3BridgeNet can only simulate one switch/bridge")
        super().add(comp=switch_comp)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> NS3BridgeNet:
        instance = super().fromJSON(simulation, json_obj)
        # TODO: FIXME
        return instance

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst=inst)

        sockets = self._get_socks_by_all_comp(inst=inst)
        for sock in sockets:
            cmd += f"--SimbricksPort={sock._path} "

        if self.opt is not None:
            cmd += f"{self.opt}"

        return cmd
