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

import typing_extensions as tpe

from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import pcie as sys_pcie
from simbricks.orchestration.system import eth as sys_eth
from simbricks.orchestration.system import nic as sys_nic
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.instantiation import socket as inst_socket
from simbricks.orchestration.simulation import base as sim_base
from simbricks.utils import base as utils_base


class PCIDevSim(sim_base.Simulator):
    """Base class for PCIe device simulators."""

    def __init__(self, simulation: sim_base.Simulation, executable: str, name: str) -> None:
        super().__init__(simulation=simulation, executable=executable, name=name)

    def full_name(self) -> str:
        return "dev." + self.name

    def supported_socket_types(self, interface: sys_base.Interface) -> set[inst_socket.SockType]:
        return {inst_socket.SockType.LISTEN}


class NICSim(PCIDevSim):
    """Base class for NIC simulators."""

    def __init__(self, simulation: sim_base.Simulation, executable: str, name: str = "") -> None:
        super().__init__(simulation=simulation, executable=executable, name=name)
        self.mac: str | None = None
        self.log_file: str | None = None

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["mac"] = self.mac
        json_obj["log_file"] = self.log_file
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(simulation, json_obj)
        instance.mac = utils_base.get_json_attr_top(json_obj, "mac")
        instance.log_file = utils_base.get_json_attr_top(json_obj, "log_file")
        return instance

    def full_name(self) -> str:
        return "nic." + self.name

    def add(self, nic: sys_nic.SimplePCIeNIC):
        assert len(self._components) < 1
        super().add(nic)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        channels = self.get_channels()

        pci_channels = sim_base.Simulator.filter_channels_by_sys_type(
            channels, sys_pcie.PCIeChannel
        )
        pci_latency, pci_sync_period, pci_run_sync = (
            sim_base.Simulator.get_unique_latency_period_sync(pci_channels)
        )

        eth_channels = sim_base.Simulator.filter_channels_by_sys_type(channels, sys_eth.EthChannel)
        eth_latency, eth_sync_period, eth_run_sync = (
            sim_base.Simulator.get_unique_latency_period_sync(eth_channels)
        )

        if eth_run_sync != pci_run_sync:
            raise Exception(
                "currently using different synchronization values for pci and eth is not supported"
            )
        run_sync = eth_run_sync
        sync_period = min(pci_sync_period, eth_sync_period)

        cmd = f"{inst.env.repo_base(relative_path=self._executable)} "

        nic_devices = self.filter_components_by_type(ty=sys_nic.SimplePCIeNIC)
        assert len(nic_devices) == 1
        nic_device = nic_devices[0]

        socket = inst.get_socket(interface=nic_device._pci_if)
        assert socket is not None and socket._type == inst_socket.SockType.LISTEN
        params_url = self.get_parameters_url(
            inst, socket, sync=run_sync, latency=pci_latency, sync_period=sync_period
        )
        cmd += f"{params_url} "

        socket = inst.get_socket(interface=nic_device._eth_if)
        assert socket is not None and socket._type == inst_socket.SockType.LISTEN
        params_url = self.get_parameters_url(
            inst, socket, sync=run_sync, latency=eth_latency, sync_period=sync_period
        )
        cmd += f"{params_url} "

        cmd += f"{self._start_tick} "

        if self.extra_args is not None:
            cmd += " " + self.extra_args

        return cmd


class I40eNicSim(NICSim):

    def __init__(self, simulation: sim_base.Simulation):
        super().__init__(
            simulation=simulation,
            executable="sims/nic/i40e_bm/i40e_bm",
        )
        self.name = f"NICSim-{self._id}"

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(simulation, json_obj)
        return instance

    def add(self, nic: sys_nic.IntelI40eNIC):
        utils_base.has_expected_type(nic, sys_nic.IntelI40eNIC)
        super().add(nic)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst)
        if self.mac:
            cmd += " " + ("".join(reversed(self.mac.split(":"))))
            if self.log_file:
                cmd += f" {self.log_file}"
        return cmd


class E1000NIC(NICSim):

    def __init__(self, simulation: sim_base.Simulation):
        super().__init__(
            simulation=simulation,
            executable="sims/nic/e1000_gem5/e1000_gem5",
        )
        self.name = f"NICSim-{self._id}"
        self.debug: bool = False

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["debug"] = self.debug
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> E1000NIC:
        instance = super().fromJSON(simulation, json_obj)
        instance.debug = utils_base.get_json_attr_top(json_obj, "debug")
        return instance

    def add(self, nic: sys_nic.IntelE1000NIC):
        utils_base.has_expected_type(nic, sys_nic.IntelE1000NIC)
        super().add(nic)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst)
        if self.mac:
            cmd += " " + ("".join(reversed(self.mac.split(":"))))
            if self.log_file:
                cmd += f" {self.log_file}"

        if self.debug:
            cmd = f"env E1000_DEBUG=1 {cmd}"

        return cmd


class CorundumBMNICSim(NICSim):
    def __init__(self, simulation: sim_base.Simulation):
        super().__init__(
            simulation=simulation,
            executable="sims/nic/corundum_bm/corundum_bm",
        )
        self.name = f"CorundumBMNICSim-{self._id}"

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        return json_obj

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        instance = super().fromJSON(simulation, json_obj)
        return instance

    def add(self, nic: sys_nic.CorundumNIC):
        utils_base.has_expected_type(nic, sys_nic.CorundumNIC)
        super().add(nic)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = super().run_cmd(inst)
        if self.mac:
            cmd += " " + ("".join(reversed(self.mac.split(":"))))
            if self.log_file:
                cmd += f" {self.log_file}"
        return cmd
