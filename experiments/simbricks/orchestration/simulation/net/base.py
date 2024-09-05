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


class NetSim(sim_base.Simulator):
    """Base class for network simulators."""

    def __init__(
        self, simulation: sim_base.Simulation, relative_executable_path: str = ""
    ) -> None:
        super().__init__(simulation, relative_executable_path=relative_executable_path)
        # TODO: do we want them here?
        self._switch_specs = []
        self._host_specs = []

    def full_name(self) -> str:
        return "net." + self.name

    def dependencies(self) -> list[sim_base.Simulator]:
        # TODO
        deps = []
        for s in self.switches:
            for n in s.netdevs:
                deps.append(n.net[0].sim)
        return deps

    # TODO
    def sockets_wait(self, env: ExpEnv) -> list[str]:
        pass

    def wait_terminate(self) -> bool:
        # TODO
        return self.wait

    def init_network(self) -> None:
        pass

    def sockets_cleanup(self, env: ExpEnv) -> list[str]:
        # TODO
        return []


class WireNet(NetSim):

    def __init__(self, simulation: sim_base.Simulation) -> None:
        super().__init__(
            simulation=simulation,
            relative_executable_path="/sims/net/wire/net_wire",
            relative_pcap_file_path=None,
        )
        # TODO: probably we want to store these in a common base class...
        self._wire_comp: eth.EthWire | None = None
        self._relative_pcap_file_path: str | None = 'relative_pcap_file_path'

    def add(self, wire: eth.EthWire):
        assert self._wire_comp is None
        super()._add_component(wire)
        self.experiment.add_network(self)
        self._wire_comp = wire

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        eth_latency = None
        sync_period = None
        run_sync = False
        channels = self._get_channels(inst=inst) 
        for channel in channels:
            sync_period = min(sync_period, channel.sync_period)
            run_sync = run_sync or channel._synchronized
            if (
                channel.sys_channel.eth_latency != eth_latency
                and eth_latency is not None
            ):
                raise Exception("non unique eth latency")
            eth_latency = channel.sys_channel.eth_latency

        assert sync_period is not None
        assert eth_latency is not None

        sockets = self._get_sockets(inst=inst)
        assert len(sockets) == 2

        cmd = inst.join_repo_base(self._relative_executable_path)
        cmd += f"{sockets[0]} {sockets[1]} {run_sync} {sync_period} {eth_latency}"

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
        relative_executable_path="/sims/net/switch/net_switch",
        relative_pcap_file_path=None,
    ) -> None:
        super().__init__(
            simulation=simulation, relative_executable_path=relative_executable_path
        )
        # TODO: probably we want to store these in a common base class...
        self._switch_spec: eth.EthSwitch | None = None
        self._relative_pcap_file_path: str | None = relative_pcap_file_path

    def add(self, switch_spec: eth.EthSwitch):
        assert self._switch_spec is None
        super()._add_component(switch_spec)
        self.experiment.add_network(self)
        self._switch_spec = switch_spec

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        assert self._switch_spec is not None

        eth_latency = None
        sync_period = None
        run_sync = False
        channels = self._get_channels(inst=inst)
        for channel in channels:
            sync_period = min(sync_period, channel.sync_period)
            run_sync = run_sync or channel._synchronized
            if (
                channel.sys_channel.eth_latency != eth_latency
                and eth_latency is not None
            ):
                raise Exception("non unique eth latency")
            eth_latency = channel.sys_channel.eth_latency

        assert sync_period is not None
        assert eth_latency is not None

        cmd = inst.join_repo_base(self._relative_executable_path)
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
            relative_executable_path="/sims/mem/memswitch/memswitch",
            relative_pcap_file_path=relative_pcap_file_path,
        )
        """AS_ID,VADDR_START,VADDR_END,MEMNODE_MAC,PHYS_START."""
        self.mem_map = []

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst)

        for m in self.mem_map:
            cmd += " -m " + f" {m[0]},{m[1]},{m[2]},"
            cmd += "".join(reversed(m[3].split(":")))
            cmd += f",{m[4]}"

        return cmd
