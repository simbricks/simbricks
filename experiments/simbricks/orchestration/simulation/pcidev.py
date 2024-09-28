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

import typing as tp
from simbricks.orchestration.system import pcie as sys_pcie
from simbricks.orchestration.system import eth as sys_eth
from simbricks.orchestration.system import nic as sys_nic
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base as sim_base


class PCIDevSim(sim_base.Simulator):
    """Base class for PCIe device simulators."""

    def __init__(
        self, simulation: sim_base.Simulation, executable: str, name: str
    ) -> None:
        super().__init__(simulation=simulation, executable=executable, name=name)

    def full_name(self) -> str:
        return "dev." + self.name

    def supported_socket_types(self) -> set[inst_base.SockType]:
        return [inst_base.SockType.LISTEN]


class NICSim(PCIDevSim):
    """Base class for NIC simulators."""

    def full_name(self) -> str:
        return "nic." + self.name

    def __init__(
        self, simulation: sim_base.Simulation, executable: str, name: str = ""
    ) -> None:
        super().__init__(simulation=simulation, executable=executable, name=name)

    def add(self, nic: sys_nic.SimplePCIeNIC):
        assert len(self._components) < 1
        super().add(nic)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        channels = self.get_channels()
        latency, sync_period, run_sync = (
            sim_base.Simulator.get_unique_latency_period_sync(channels=channels)
        )

        cmd = f"{inst.join_repo_base(relative_path=self._executable)} "

        pci_devices = self.filter_components_by_type(ty=sys_pcie.PCIeSimpleDevice)
        assert len(pci_devices) == 1
        socket = self._get_socket(inst=inst, interface=pci_devices[0]._pci_if)
        assert socket is not None and socket._type == inst_base.SockType.LISTEN
        cmd += f"{socket._path} "

        eth_devices = self.filter_components_by_type(ty=sys_eth.EthSimpleNIC)
        assert len(eth_devices) == 1
        socket = self._get_socket(inst=inst, interface=eth_devices[0]._eth_if)
        assert socket is not None and socket._type == inst_base.SockType.LISTEN
        cmd += f"{socket._path} "

        cmd += (
            f" {inst.get_simulator_shm_pool_path(sim=self)} {int(run_sync)} {self._start_tick}"
            f" {sync_period} {latency} {latency}"
        )

        # if self.mac is not None:  # TODO: FIXME
        #     cmd += " " + ("".join(reversed(self.mac.split(":"))))

        if self.extra_args is not None:
            cmd += " " + self.extra_args

        return cmd


class I40eNicSim(NICSim):
 
    def __init__(self, simulation: sim_base.Simulation):
        super().__init__(
            simulation=simulation,
            executable="sims/nic/i40e_bm/i40e_bm",
        )
        self.name=f"NICSim-{self._id}"

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        return super().run_cmd(inst=inst)


class CorundumBMNICSim(NICSim):
    def __init__(self, simulation: sim_base.Simulation):
        super().__init__(
            simulation=simulation,
            executable="sims/nic/corundum_bm/corundum_bm",
        )
        self.name=f"CorundumBMNICSim-{self._id}"

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst=inst)
        return cmd


class CorundumVerilatorNICSim(NICSim):

    def __init__(self, simulation: sim_base.Simulation):
        super().__init__(
            simulation=simulation,
            executable="sims/nic/corundum/corundum_verilator",
        )
        self.name=f"CorundumVerilatorNICSim-{self._id}"
        self.clock_freq = 250  # MHz

    def resreq_mem(self) -> int:
        # this is a guess
        return 512

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst=inst)
        cmd += f" {self.clock_freq}"
        return cmd
