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
Script for HOMA large scale benchmark. 40 hosts.
"""

import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim
from simbricks.orchestration.simulator_utils import create_basic_hosts

host_types = ['qemu', 'gem5', 'qt']
net_types = ['sw', 'ns3']
num_node = [2, 5, 10, 20, 40]
experiments = []

# Create multiple experiments with different simulator permutations, which can
# be filtered later.
for host_type in host_types:
    for net_type in net_types:
        for n in num_node: 
            e = exp.Experiment(
                'homa-' + host_type + '-' + net_type + f'-{n}'
            )

            # network
            if net_type == 'sw':
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

                def qemu_timing(node_config: node.NodeConfig):
                    h = sim.QemuHost(node_config)
                    h.sync = True
                    return h

                HostClass = qemu_timing
            elif host_type == 'gem5':
                HostClass = sim.Gem5Host
                e.checkpoint = True
            else:
                raise NameError(host_type)

            # nic
            NicClass = sim.I40eNIC
            NcClass = node.I40eLinuxNode


            # create servers and clients
            nodes = create_basic_hosts(
                e,
                n,
                'node',
                net,
                NicClass,
                HostClass,
                NcClass,
                node.HomaCluster
            )

            nodes[0].node_config.app.is_node_zero = True
            for c in nodes:
                c.node_config.disk_image = 'homa'
                c.wait = True

            # add to experiments
            experiments.append(e)
