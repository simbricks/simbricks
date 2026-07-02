# Copyright 2026 Max Planck Institute for Software Systems,
# National University of Singapore, and SimBricks UG (haftungsbeschränkt)
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

import typing_extensions as tpe

from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.simulation.net import net_base
from simbricks.orchestration.system import eth as sys_eth
from simbricks.utils import base as utils_base


class WireNet(net_base.NetSim):

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
        utils_base.has_expected_type(wire, sys_eth.EthWire)
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
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(simulation, json_obj)
        instance._relative_pcap_file_path = utils_base.get_json_attr_top(json_obj, "relative_pcap_file_path")
        return instance

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        channels = self.get_channels()
        eth_latency, sync_period, run_sync = (
            sim_base.Simulator.get_unique_latency_period_sync(channels=channels)
        )

        sockets = self._get_socks_by_all_comp(inst=inst)
        assert len(sockets) == 2

        cmd = inst.env.repo_base(self._executable)
        cmd += f"{sockets[0]._path} {sockets[1]._path} {run_sync} {sync_period} {eth_latency}"

        if self._relative_pcap_file_path is not None:
            pcap_file = inst.env.output_base(
                relative_path=self._relative_pcap_file_path
            )
            cmd += " -p " + pcap_file
        return cmd


class SwitchNet(net_base.NetSim):

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
        utils_base.has_expected_type(switch_spec, sys_eth.EthSwitch)
        if len(self._components) > 1:
            raise Exception("can only add a single switch component to the SwitchNet")
        super().add(switch_spec)

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["relative_pcap_file_path"] = self._relative_pcap_file_path
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(simulation, json_obj)
        instance._relative_pcap_file_path = utils_base.get_json_attr_top(json_obj, "relative_pcap_file_path")
        return instance

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        channels = self.get_channels()
        eth_latency, sync_period, run_sync = (
            sim_base.Simulator.get_unique_latency_period_sync(channels=channels)
        )

        cmd = inst.env.repo_base(self._executable)
        cmd += f" -S {sync_period} -E {eth_latency}"

        if not run_sync:
            cmd += " -u"

        if self._relative_pcap_file_path is not None:
            pcap_file = inst.env.output_base(
                relative_path=self._relative_pcap_file_path
            )
            cmd += " -p " + pcap_file

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
            relative_pcap_filepath=relative_pcap_file_path,
        )
        self.name = f"MemSwitchNet-{self._id}"
        """AS_ID,VADDR_START,VADDR_END,MEMNODE_MAC,PHYS_START."""
        self.mem_map = []

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        # TODO: FIXME
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
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
