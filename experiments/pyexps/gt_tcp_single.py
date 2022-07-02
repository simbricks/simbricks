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

# iperf TCP_single test
# naming convention following host-nic-net-app
# host: gem5-timing
# nic:  cv/cb/ib
# net:  wire/switch/dumbbell/bridge
# app: TCPs

kinds_of_host = ['gem5-timing']
kinds_of_nic = ['cv', 'cb', 'ib']
kinds_of_net = ['wire', 'switch', 'dumbbell', 'bridge']
kinds_of_app = ['TCPs']

experiments = []

# set network sim
for n in kinds_of_net:
    if n == 'wire':
        NetClass = sim.WireNet
    if n == 'switch':
        NetClass = sim.SwitchNet
    if n == 'dumbbell':
        NetClass = sim.NS3DumbbellNet
    if n == 'bridge':
        NetClass = sim.NS3BridgeNet

    # set nic sim
    for c in kinds_of_nic:
        net = NetClass()
        e = exp.Experiment('gt-' + c + '-' + n + '-' + 'TCPs')
        e.checkpoint = True
        e.add_network(net)

        if c == 'cv':
            servers = create_basic_hosts(
                e,
                1,
                'server',
                net,
                sim.CorundumVerilatorNIC,
                sim.Gem5Host,
                node.CorundumLinuxNode,
                node.IperfTCPServer
            )
            clients = create_basic_hosts(
                e,
                1,
                'client',
                net,
                sim.CorundumVerilatorNIC,
                sim.Gem5Host,
                node.CorundumLinuxNode,
                node.IperfTCPClient,
                ip_start=2
            )

        if c == 'cb':
            servers = create_basic_hosts(
                e,
                1,
                'server',
                net,
                sim.CorundumBMNIC,
                sim.Gem5Host,
                node.CorundumLinuxNode,
                node.IperfTCPServer
            )
            clients = create_basic_hosts(
                e,
                1,
                'client',
                net,
                sim.CorundumBMNIC,
                sim.Gem5Host,
                node.CorundumLinuxNode,
                node.IperfTCPClient,
                ip_start=2
            )

        if c == 'ib':
            servers = create_basic_hosts(
                e,
                1,
                'server',
                net,
                sim.I40eNIC,
                sim.Gem5Host,
                node.I40eLinuxNode,
                node.IperfTCPServer
            )
            clients = create_basic_hosts(
                e,
                1,
                'client',
                net,
                sim.I40eNIC,
                sim.Gem5Host,
                node.I40eLinuxNode,
                node.IperfTCPClient,
                ip_start=2
            )

        clients[0].wait = True
        clients[0].node_config.app.server_ip = servers[0].node_config.ip

        print(e.name)
        experiments.append(e)
