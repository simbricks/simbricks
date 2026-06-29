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

from simbricks.components.nvmessd import system as sys_nvmessd
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.system import pcie as sys_pcie
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.simulation import pcidev
from simbricks.utils import base as utils_base


class FEMUSim(pcidev.PCIDevSim):

    def __init__(self, simulation: sim_base.Simulation) -> None:
        super().__init__(
            simulation=simulation, executable="sims/external/femu/femu-simbricks", name=""
        )
        self.name = f"FEMUSim-{self._id}"

    @classmethod
    def fromJSON(cls, simulation: sim_base.Simulation, json_obj: dict) -> tpe.Self:
        return super().fromJSON(simulation, json_obj)

    def add(self, ssd: sys_nvmessd.NVMeSSD):
        utils_base.has_expected_type(ssd, sys_nvmessd.NVMeSSD)
        super().add(ssd)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        cmd = f"{inst.env.repo_base(relative_path=self._executable)} "

        nvme_devices = self.filter_components_by_type(ty=sys_nvmessd.NVMeSSD)
        assert len(nvme_devices) == 1
        nvme_dev = nvme_devices[0]
        socket = inst.get_socket(interface=nvme_dev._pci_if)

        pci_channels = sim_base.Simulator.filter_channels_by_sys_type(
            self.get_channels(), sys_pcie.PCIeChannel
        )
        pci_latency, pci_sync_period, pci_run_sync = (
            sim_base.Simulator.get_unique_latency_period_sync(pci_channels)
        )
        params_url = self.get_parameters_url(
            inst, socket, sync=pci_run_sync, latency=pci_latency, sync_period=pci_sync_period
        )
        cmd += f"{params_url} "

        return cmd
