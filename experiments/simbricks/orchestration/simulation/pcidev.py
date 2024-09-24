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

import simbricks.orchestration.system as sys_conf
import typing as tp
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.simulation import base


class PCIDevSim(base.Simulator):
    """Base class for PCIe device simulators."""

    def __init__(self, e: base.Simulation) -> None:
        super().__init__(e)

        self.start_tick = 0
        """The timestamp at which to start the simulation. This is useful when
        the simulator is only attached at a later point in time and needs to
        synchronize with connected simulators. For example, this could be used
        when taking checkpoints to only attach certain simulators after the
        checkpoint has been taken."""

    def full_name(self) -> str:
        return 'dev.' + self.name

    def is_nic(self) -> bool:
        return False

    def sockets_cleanup(self, inst: inst_base.Instantiation) -> tp.List[str]:
        return [inst_base.Socket(f'{inst._env._workdir}/dev.pci.{self.name}'),  inst_base.Socket(f' {inst._env._shm_base}/dev.shm.{self.name}')]

    def sockets_wait(self, inst: inst_base.Instantiation) -> tp.List[str]:

        return [inst_base.Socket(f'{inst._env._workdir}/dev.pci.{self.name}')]



class NICSim(PCIDevSim):
    """Base class for NIC simulators."""

    def __init__(self, e: base.Simulation) -> None:
        super().__init__(e)
        self.start_tick = 0
        self.name = f'{self._id}'

    def add(self, nic: sys_conf.SimplePCIeNIC):
        super().add(nic)

    def basic_args(self, inst: inst_base.Instantiation, extra: tp.Optional[str] = None) -> str:
        # TODO: need some fix. how to handle multiple nics in one simulator?
        for c in self._components:
            nic_comp = c
        nic_pci_chan_comp = nic_comp._pci_if.channel
        nic_eth_chan_comp = nic_comp._eth_if.channel
        nic_pci_chan_sim = self._simulation.retrieve_or_create_channel(nic_pci_chan_comp)
        nic_eth_chan_sim = self._simulation.retrieve_or_create_channel(nic_eth_chan_comp)


        cmd = (
            f'{inst._env._workdir}/dev.pci.{self.name} {inst._env._workdir}/nic.eth.{self.name}'
            f' {inst._env._shm_base}/dev.shm.{self.name} {nic_pci_chan_sim._synchronized} {self.start_tick}'
            f' {nic_pci_chan_sim.sync_period} {nic_pci_chan_comp.latency} {nic_eth_chan_comp.latency}'
        )
        # if nic_comp.mac is not None:
        #     cmd += ' ' + (''.join(reversed(nic_comp.mac.split(':'))))

        if extra is not None:
            cmd += ' ' + extra
        return cmd

    def basic_run_cmd(
        self, inst: inst_base.Instantiation, name: str, extra: tp.Optional[str] = None
    ) -> str:
        cmd = f'{inst._env._repodir}/sims/nic/{name} {self.basic_args(inst, extra)}'
        return cmd

    def full_name(self) -> str:
        return 'nic.' + self.name

    def is_nic(self) -> bool:
        return True

    def sockets_cleanup(self, inst: inst_base.Instantiation) -> tp.List[str]:
        for c in self._components:
            nic_comp = c
        return super().sockets_cleanup(inst) + [inst_base.Socket(f'{inst._env._workdir}/nic.eth.{self.name}')]

    def sockets_wait(self, inst: inst_base.Instantiation) -> tp.List[str]:
        for c in self._components:
            nic_comp = c
        return super().sockets_wait(inst) + [inst_base.Socket(f'{inst._env._workdir}/nic.eth.{self.name}')]


class I40eNicSim(NICSim):

    def __init__(self, e: 'Simulation'):
        super().__init__(e)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        return self.basic_run_cmd(inst, '/i40e_bm/i40e_bm')


class CorundumBMNICSim(NICSim):
    def __init__(self, e: 'Simulation'):
        super().__init__(e)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        return self.basic_run_cmd(inst, '/corundum_bm/corundum_bm')




class CorundumVerilatorNICSim(NICSim):

    def __init__(self, e: 'Simulation'):
        super().__init__(e)
        self.clock_freq = 250  # MHz

    def resreq_mem(self) -> int:
        # this is a guess
        return 512

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        print("run cmd")
        print(self.basic_run_cmd(inst, '/corundum/corundum_verilator'))

        return self.basic_run_cmd(
            inst, '/corundum/corundum_verilator', str(self.clock_freq)
        )
