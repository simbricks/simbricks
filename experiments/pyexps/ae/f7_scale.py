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

########################################################################
# This script is for reproducing [Figure 7] scalability result.
# It generates experiments that simulating varying number of hosts.
#
# We used following combination of simulators.
# HOST: Gem5 timing CPU
# NIC: Intel i40e behavioral model
# NET: Switch behavioral model
#
# In each simulation, one server host and several clients are connected by a
# switch
# [HOST_0] - [NIC_0] ---- [SWITCH] ----  [NIC_1] - [HOST_1]
#  server                  | .....|                client_0
#                     Client_1  Clinet_n
#
# The server host runs iperf UDP server and client host runs UDP test
# The total aggregated bandwidth sent to the server are fixed to 1000 Mbps
#
# The command to run all the experiments is:
# $: python3 run.py pyexps/ae/f7_scale.py --filter host-gt-ib-sw-* --verbose
########################################################################

import simbricks.nodeconfig as node
import simbricks.simulators as sim
from simbricks.simulator_utils import create_basic_hosts

import simbricks.experiments as exp

host_types = ['gt']
nic_types = ['ib']
net_types = ['sw']
app = ['Host']

total_rate = 1000  # Mbps
num_client_max = 8
num_client_step = 2
num_client_types = [1, 4, 9, 14, 20]

experiments = []

for n_client in num_client_types:

    per_client_rate = int(total_rate / n_client)
    rate = f'{per_client_rate}m'

    for host_type in host_types:
        for nic_type in nic_types:
            for net_type in net_types:

                e = exp.Experiment(
                    'host-' + host_type + '-' + nic_type + '-' + net_type +
                    '-' + f'{total_rate}m' + f'-{n_client}'
                )
                # network
                if net_type == 'sw':
                    net = sim.SwitchNet()
                elif net_type == 'br':
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
                elif host_type == 'gt':
                    HostClass = sim.Gem5Host
                    e.checkpoint = True
                else:
                    raise NameError(host_type)

                # nic
                if nic_type == 'ib':
                    NicClass = sim.I40eNIC
                    NcClass = node.I40eLinuxNode
                elif nic_type == 'cb':
                    NicClass = sim.CorundumBMNIC
                    NcClass = node.CorundumLinuxNode
                elif nic_type == 'cv':
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
                    node.IperfUDPServer
                )

                clients = create_basic_hosts(
                    e,
                    n_client,
                    'client',
                    net,
                    NicClass,
                    HostClass,
                    NcClass,
                    node.IperfUDPClient,
                    ip_start=2
                )

                clients[n_client - 1].node_config.app.is_last = True
                clients[n_client - 1].wait = True

                for c in clients:
                    c.node_config.app.server_ip = servers[0].node_config.ip
                    c.node_config.app.rate = rate
                    c.cpu_freq = '3GHz'
                    #c.wait = True

                servers[0].cpu_freq = '3GHz'

                print(e.name)

                # add to experiments
                experiments.append(e)
