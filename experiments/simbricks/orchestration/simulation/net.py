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

import simbricks.orchestration.simulation.base as base
import simbricks.orchestration.system as system
import typing as tp
import simbricks.orchestration.experiments as exp
from simbricks.orchestration.experiment.experiment_environment_new import ExpEnv

class NetSim(Simulator):
    """Base class for network simulators."""

    def __init__(self, e: exp.Experiment) -> None:
        super().__init__(e)
        self.opt = ''
        self.switches: tp.List[spec.Switch] = []
        self.nicSim: tp.List[I40eNicSim] = []
        self.wait = False

    def full_name(self) -> str:
        return 'net.' + self.name
    
    def add(self, switch: spec.Switch):
        self.switches.append(switch)
        # switch.sim = self
        self.experiment.add_network(self)
        self.name = f'{switch.id}'


        for ndev in switch.netdevs:
            
            self.nicSim.append(n.net[0].sim)

    def connect_sockets(self, env: ExpEnv) -> tp.List[tp.Tuple[Simulator, str]]:
        sockets = []
        for n in self.nicSim:
            sockets.append((n, env.nic_eth_path(n)))
        return sockets    

    def dependencies(self) -> tp.List[Simulator]:
        deps = []
        for s in self.switches:
            for n in s.netdevs:
                deps.append(n.net[0].sim)
        return deps
    
    def sockets_cleanup(self, env: ExpEnv) -> tp.List[str]:
        pass

    def sockets_wait(self, env: ExpEnv) -> tp.List[str]:
        pass

    def wait_terminate(self) -> bool:
        return self.wait

    def init_network(self) -> None:
        pass

    def sockets_cleanup(self, env: ExpEnv) -> tp.List[str]:
        cleanup = []
        return cleanup
    


class SwitchBMSim(NetSim):

    def __init__(self, e: exp.Experiment):
        super().__init__(e)

    def run_cmd(self, env: ExpEnv) -> str:
        cmd = env.repodir + '/sims/net/switch/net_switch'
        cmd += f' -S {self.switches[0].sync_period} -E {self.switches[0].eth_latency}'

        if not self.switches[0].sync:
            cmd += ' -u'

        if len(env.pcap_file) > 0:
            cmd += ' -p ' + env.pcap_file
        for (_, n) in self.connect_sockets(env):
            cmd += ' -s ' + n
        # for (_, n) in self.listen_sockets(env):
        #     cmd += ' -h ' + n
        return cmd