# Copyright 2021 Max Planck Institute for Software Systems, and
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
Experiment, which simulates two hosts, one running a netperf server and the
other a client with the goal of measuring latency and throughput between them.

The goal is to compare different simulators for host, NIC, and the network in
terms of simulated network throughput and latency.
"""

import simbricks.nodeconfig as node
import simbricks.simulators as sim
from simbricks.simulator_utils import create_basic_hosts

import simbricks.experiments as exp

host_types = ['qemu', 'gem5', 'qt']
nic_types = ['i40e', 'cd_bm', 'cd_verilator']
net_types = ['switch', 'ns3']
experiments = []

# Create multiple experiments with different simulator permutations, which can
# be filtered later.
for host_type in host_types:
    for nic_type in nic_types:
        for net_type in net_types:
            e = exp.Experiment(
                'netperf-' + host_type + '-' + net_type + '-' + nic_type
            )

            # network
            if net_type == 'switch':
                net = sim.SwitchNet()
            elif net_type == 'ns3':
                net = sim.NS3BridgeNet()
            else:
                raise NameError(net_type)
            e.add_network(net)

            # host
            if host_type == 'qemu':
                HostClass = sim.QemuHost
            elif host_type == 'qt':

                def qemu_timing():
                    h = sim.QemuHost()
                    h.sync = True
                    return h

                HostClass = qemu_timing
            elif host_type == 'gem5':
                HostClass = sim.Gem5Host
                e.checkpoint = True
            else:
                raise NameError(host_type)

            # nic
            if nic_type == 'i40e':
                NicClass = sim.I40eNIC
                NcClass = node.I40eLinuxNode
            elif nic_type == 'cd_bm':
                NicClass = sim.CorundumBMNIC
                NcClass = node.CorundumLinuxNode
            elif nic_type == 'cd_verilator':
                NicClass = sim.CorundumVerilatorNIC
                NcClass = node.CorundumLinuxNode
            else:
                raise NameError(nic_type)

            # create servers and clients
            servers = create_basic_hosts(
                e,
                1,
                'server',
                net,
                NicClass,
                HostClass,
                NcClass,
                node.NetperfServer
            )

            clients = create_basic_hosts(
                e,
                1,
                'client',
                net,
                NicClass,
                HostClass,
                NcClass,
                node.NetperfClient,
                ip_start=2
            )

            for c in clients:
                c.wait = True
                c.node_config.app.server_ip = servers[0].node_config.ip

            # add to experiments
            experiments.append(e)
