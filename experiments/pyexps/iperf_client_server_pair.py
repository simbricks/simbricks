# Copyright 2023 Max Planck Institute for Software Systems, and
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
"""
Two hosts connected by a switch. Both run iPerf where one host is the client and
the other the server.

This module creates multiple experiments for comparing multiple host and NIC
simulator combinations. Client and Server use the same simulators.
"""

from simbricks.orchestration import experiments as exp
from simbricks.orchestration import nodeconfig, simulator_utils, simulators

host_types = ['qemu', 'gem5', 'simics']
nic_types = ['i40e', 'e1000']
experiments = []


class QemuTiming(simulators.QemuHost):

    def __init__(self, node_config):
        super().__init__(node_config)
        self.sync = True


class Gem5Timing(simulators.Gem5Host):

    def __init__(self, node_config):
        super().__init__(node_config)
        self.cpu_type = 'TimingSimpleCPU'
        self.cpu_type_cp = 'TimingSimpleCPU'


for host_type in host_types:
    for nic_type in nic_types:
        e = exp.Experiment(f'iperf-{host_type}-{nic_type}-pair')
        net = simulators.SwitchNet()
        e.add_network(net)

        if host_type == 'qemu':
            HostClass = QemuTiming
        elif host_type == 'gem5':
            HostClass = Gem5Timing
            e.checkpoint = True
        elif host_type == 'simics':
            HostClass = simulators.SimicsHost
        else:
            raise NameError(host_type)

        if nic_type == 'i40e':
            NicClass = simulators.I40eNIC
            NodeConfigClass = nodeconfig.I40eLinuxNode
        elif nic_type == 'e1000':
            NicClass = simulators.E1000NIC
            NodeConfigClass = nodeconfig.E1000LinuxNode
        else:
            raise NameError(nic_type)

        servers = simulator_utils.create_basic_hosts(
            e,
            1,
            'server',
            net,
            NicClass,
            HostClass,
            NodeConfigClass,
            nodeconfig.IperfTCPServer
        )

        clients = simulator_utils.create_basic_hosts(
            e,
            1,
            'client',
            net,
            NicClass,
            HostClass,
            NodeConfigClass,
            nodeconfig.IperfTCPClient,
            ip_start=2
        )

        for c in clients:
            c.wait = True
            c.node_config.app.server_ip = servers[0].node_config.ip

        experiments.append(e)
