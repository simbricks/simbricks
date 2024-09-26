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

import abc
import sys
import simbricks.orchestration.simulation.base as sim_base
from simbricks.orchestration.system import eth
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.experiment.experiment_environment_new import ExpEnv
from simbricks.orchestration.utils import base as base_utils


class NetSim(sim_base.Simulator):
    """Base class for network simulators."""

    def __init__(
        self,
        simulation: sim_base.Simulation,
        executable: str,
        name: str,
    ) -> None:
        super().__init__(simulation=simulation, executable=executable, name=name)

    def full_name(self) -> str:
        return "net." + self.name

    def init_network(self) -> None:
        pass

    def supported_socket_types(self) -> set[inst_base.SockType]:
        return [inst_base.SockType.CONNECT]


class WireNet(NetSim):

    def __init__(
        self, simulation: sim_base.Simulation, relative_pcap_filepath: str | None = None
    ) -> None:
        super().__init__(
            simulation=simulation,
            executable="sims/net/wire/net_wire",
            name=f"WireNet-{self._id}",
        )
        self._relative_pcap_file_path: str | None = relative_pcap_filepath

    def add(self, wire: eth.EthWire):
        base_utils.has_expected_type(wire, eth.EthWire)
        if len(self._components) > 1:
            raise Exception(
                "can only add a single wire component to the WireNet simulator"
            )
        super().add(wire)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        channels = self.get_channels()
        eth_latency, sync_period, run_sync = (
            sim_base.Simulator.get_unique_latency_period_sync(channels=channels)
        )

        sockets = self._get_sockets(inst=inst)
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
            name=f"SwitchNet-{self._id}",
        )
        self._relative_pcap_file_path: str | None = relative_pcap_filepath

    def add(self, switch_spec: eth.EthSwitch):
        base_utils.has_expected_type(switch_spec, eth.EthSwitch)
        if len(self._components) > 1:
            raise Exception("can only add a single switch component to the SwitchNet")
        super().add(switch_spec)

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

        sockets = self._get_sockets(inst=inst)
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
        self._name = f"MemSwitchNet-{self._id}"
        """AS_ID,VADDR_START,VADDR_END,MEMNODE_MAC,PHYS_START."""
        self.mem_map = []

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst)

        for m in self.mem_map:
            cmd += " -m " + f" {m[0]},{m[1]},{m[2]},"
            cmd += "".join(reversed(m[3].split(":")))
            cmd += f",{m[4]}"

        return cmd
