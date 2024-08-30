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

import simbricks.orchestration.simulation as sim_conf
import simbricks.orchestration.system as sys_conf
import typing as tp
from simbricks.orchestration.experiment.experiment_environment_new import ExpEnv


class PCIDevSim(sim_conf.Simulator):
    """Base class for PCIe device simulators."""

    def __init__(self, e: sim_conf.Simulation) -> None:
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

    def sockets_cleanup(self, env: ExpEnv) -> tp.List[str]:
        return [env.dev_pci_path(self), env.dev_shm_path(self)]

    def sockets_wait(self, env: ExpEnv) -> tp.List[str]:
        return [env.dev_pci_path(self)]



class NICSim(PCIDevSim):
    """Base class for NIC simulators."""

    def __init__(self, e: sim_conf.Simulation) -> None:
        super().__init__(e)
        self.experiment = e
        self.nics: tp.List[sim_conf.PCIDevSim] = []
        self.start_tick = 0

    def add(self, nic: sim_conf.PCIDevSim):
        self.nics.append(nic)
        # nic.sim = self
        self.experiment.add_nic(self)
        self.name = f'{nic.id}'

    def basic_args(self, env: ExpEnv, extra: tp.Optional[str] = None) -> str:
        cmd = (
            f'{env.dev_pci_path(self)} {env.nic_eth_path(self)}'
            f' {env.dev_shm_path(self)} {self.nics[0].sync} {self.start_tick}'
            f' {self.nics[0].sync_period} {self.nics[0].pci_channel.latency} {self.nics[0].eth_channel.latency}'
        )
        if self.nics[0].mac is not None:
            cmd += ' ' + (''.join(reversed(self.nics[0].mac.split(':'))))

        if extra is not None:
            cmd += ' ' + extra
        return cmd

    def basic_run_cmd(
        self, env: ExpEnv, name: str, extra: tp.Optional[str] = None
    ) -> str:
        cmd = f'{env.repodir}/sims/nic/{name} {self.basic_args(env, extra)}'
        return cmd

    def full_name(self) -> str:
        return 'nic.' + self.name

    def is_nic(self) -> bool:
        return True

    def sockets_cleanup(self, env: ExpEnv) -> tp.List[str]:
        return super().sockets_cleanup(env) + [env.nic_eth_path(self)]

    def sockets_wait(self, env: ExpEnv) -> tp.List[str]:
        return super().sockets_wait(env) + [env.nic_eth_path(self)]


class I40eNicSim(NICSim):

    def __init__(self, e: sim_conf.Simulation):
        super().__init__(e)

    def run_cmd(self, env: ExpEnv) -> str:
        return self.basic_run_cmd(env, '/i40e_bm/i40e_bm')


class CorundumBMNICSim(NICSim):
    def __init__(self, e: sim_conf.Simulation):
        super().__init__(e)

    def run_cmd(self, env: ExpEnv) -> str:
        return self.basic_run_cmd(env, '/corundum_bm/corundum_bm')




class CorundumVerilatorNICSim(NICSim):

    def __init__(self, e: sim_conf.Simulation):
        super().__init__(e)
        self.clock_freq = 250  # MHz

    def resreq_mem(self) -> int:
        # this is a guess
        return 512

    def run_cmd(self, env: ExpEnv) -> str:
        return self.basic_run_cmd(
            env, '/corundum/corundum_verilator', str(self.clock_freq)
        )
