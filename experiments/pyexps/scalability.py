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

import simbricks.nodeconfig as node
import simbricks.simulators as sim
from simbricks.simulator_utils import create_basic_hosts

import simbricks.experiments as exp

host_configs = ['bm', 'cycle']
n_clients = [1, 2, 4, 8]
target_bandwidth = 100

experiments = []

for host_config in host_configs:
    for nc in n_clients:
        e = exp.Experiment('scalability-' + host_config + '-' + str(nc))

        if host_config == 'bm':
            host_class = sim.QemuHost
            nic_class = sim.CorundumBMNIC
            nc_class = node.CorundumLinuxNode
            net = sim.SwitchNet()
        elif host_config == 'cycle':
            host_class = sim.Gem5Host
            nic_class = sim.CorundumVerilatorNIC
            nc_class = node.CorundumLinuxNode
            net = sim.NS3BridgeNet()
        else:
            raise NameError(host_config)

        e.add_network(net)

        servers = create_basic_hosts(
            e,
            1,
            'server',
            net,
            nic_class,
            host_class,
            nc_class,
            node.IperfUDPServer
        )

        clients = create_basic_hosts(
            e,
            nc,
            'client',
            net,
            nic_class,
            host_class,
            nc_class,
            node.IperfUDPClient
        )

        for c in clients:
            c.wait = True
            c.node_config.app.server_ip = servers[0].node_config.ip
            c.node_config.app.rate = str(target_bandwidth / nc) + 'm'

        experiments.append(e)
